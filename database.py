import sqlite3
import json
from datetime import datetime

DB_PATH = "essay_grader.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            exam_level TEXT NOT NULL DEFAULT 'HCL',
            genre TEXT NOT NULL,
            prompt TEXT NOT NULL,
            requirements TEXT,
            rubric TEXT,
            focus_areas TEXT,
            created_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    try:
        c.execute("ALTER TABLE assignments ADD COLUMN focus_areas TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE assignments ADD COLUMN exam_level TEXT DEFAULT 'HCL'")
    except:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            submitted_at TEXT,
            image_data BLOB,
            ocr_text TEXT,
            feedback_json TEXT,
            viewed_at TEXT,
            FOREIGN KEY (assignment_id) REFERENCES assignments(id)
        )
    """)
    try:
        c.execute("ALTER TABLE submissions ADD COLUMN ocr_text TEXT")
    except:
        pass

    # ════════════════════════════════════════════════════════════════
    # 成长档案：essay_records（每篇一行，跨篇查询主力表）
    # 这是 submissions.feedback_json 的“可查询投影”，原始 JSON 永不丢弃。
    # 提取出错可随时用 backfill_growth_data() 从 feedback_json 重建。
    # ════════════════════════════════════════════════════════════════
    c.execute("""
        CREATE TABLE IF NOT EXISTS essay_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL UNIQUE,
            student_id TEXT NOT NULL,
            student_name TEXT,
            assignment_id INTEGER,
            exam_level TEXT,
            genre TEXT,
            topic_type TEXT,
            raw_content INTEGER,
            raw_language INTEGER,
            raw_total INTEGER,
            display_total INTEGER,
            grade TEXT,
            is_handwritten INTEGER DEFAULT 1,
            graded_at TEXT,
            FOREIGN KEY (submission_id) REFERENCES submissions(id)
        )
    """)

    # ════════════════════════════════════════════════════════════════
    # 成长档案：error_tags（每个问题一行，统计/排行榜主力表）
    # error_category 用固定枚举（见 ERROR_CATEGORIES），才能 GROUP BY。
    # severity: 'red'=机械错误(错字病句标点) / 'green'=思维问题(详略/论证/审题)
    # ════════════════════════════════════════════════════════════════
    c.execute("""
        CREATE TABLE IF NOT EXISTS error_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            student_id TEXT NOT NULL,
            error_category TEXT NOT NULL,
            severity TEXT,
            para_role TEXT,
            detail TEXT,
            graded_at TEXT,
            FOREIGN KEY (submission_id) REFERENCES submissions(id)
        )
    """)

    # 查询索引（学生维度的跨篇查询是最高频操作）
    c.execute("CREATE INDEX IF NOT EXISTS idx_records_student ON essay_records(student_id, graded_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tags_student ON error_tags(student_id, error_category)")

    conn.commit()
    conn.close()

# ════════════════════════════════════════════════════════════════════
# 成长档案：错误分类固定枚举 + 提取 + 查询
# ════════════════════════════════════════════════════════════════════

# error_category 固定枚举。分两类 severity：
#   red  = 机械错误（学生看到正确写法就懂）
#   green= 思维/内容问题（需要解释才懂，对应你 prompt 里的内容严格维度）
# 这套枚举可扩展，但务必固定 key，否则统计会碎掉。
ERROR_CATEGORIES = {
    # red 机械错误
    "错别字":       "red",
    "标点错误":     "red",
    "病句":         "red",
    "词汇贫乏":     "red",
    # green 思维/内容问题
    "详略失衡":     "green",
    "抒情议论缺失": "green",
    "核心情节略写": "green",
    "论证跳跃":     "green",
    "审题偏差":     "green",
    "结构混乱":     "green",
}

# 把 AI 自由文本的问题类型，归一到上面的固定 category。
# AI 的 red_issues[].type / green_issues[].type 用词不统一，这里做关键词映射。
def _normalize_error_category(raw_type, severity_hint):
    """把 AI 返回的问题类型字符串归一到 ERROR_CATEGORIES 的固定 key。"""
    t = (raw_type or "").strip()
    # 关键词命中（顺序敏感：先具体后宽泛）
    rules = [
        ("错别字", ["错别字", "错字", "别字", "写错"]),
        ("标点错误", ["标点", "符号"]),
        ("词汇贫乏", ["词汇", "用词不当", "用词", "词语"]),
        ("详略失衡", ["详略", "失衡", "废话", "注水", "啰嗦", "冗余", "略写太"]),
        ("抒情议论缺失", ["抒情", "议论", "升华", "感悟", "中心"]),
        ("核心情节略写", ["核心情节", "高潮", "略写", "一笔带过", "经过不"]),
        ("论证跳跃", ["论证", "逻辑", "跳跃", "断层", "论据", "peel", "说理"]),
        ("审题偏差", ["审题", "偏题", "跑题", "离题", "题意", "关键词"]),
        ("结构混乱", ["结构", "组织", "条理", "段落安排", "衔接"]),
        ("病句", ["病句", "不通", "弱句", "语句"]),
    ]
    low = t.lower()
    for cat, kws in rules:
        for kw in kws:
            if kw.lower() in low:
                return cat
    # 没命中：按 severity 兜底（red→病句，green→结构混乱），保证不丢数据
    return "病句" if severity_hint == "red" else "结构混乱"


def _parse_grade(feedback):
    """从 feedback 里取等级字符串（A1-F9），尽量不空。"""
    g = (feedback.get("grade_estimate") or "").strip()
    if not g:
        return ""
    # 只取前两位字母数字，防止 'B4（中上）' 这种带后缀
    import re
    m = re.match(r"[A-Fa-f]\s*\d", g)
    return m.group(0).replace(" ", "").upper() if m else g[:2].upper()


def extract_growth_data(conn, submission_id, student_id, student_name,
                        assignment, feedback, is_handwritten=True):
    """从一份 feedback（dict）提取结构化行，写入 essay_records + error_tags。
    挂在 save_submission 内部调用，存提交时自动完成，调用方无需改动。
    全程 .get() 防御：兜底场景下 feedback 可能缺字段，缺了就跳过、不报错。
    """
    if not isinstance(feedback, dict):
        return
    c = conn.cursor()
    now = datetime.now().isoformat()

    scores = feedback.get("scores", {}) or {}
    raw_content = scores.get("content")
    raw_language = scores.get("language")
    raw_total = scores.get("total")
    grade = _parse_grade(feedback)

    topic_type = ""
    ta = feedback.get("topic_analysis", {}) or {}
    if isinstance(ta, dict):
        topic_type = (ta.get("type") or "").strip()

    exam_level = (assignment or {}).get("exam_level", "")
    genre = (assignment or {}).get("genre", "")
    assignment_id = (assignment or {}).get("id")

    # 1) essay_records：每篇一行。display_total 先 = raw_total（校准时再单独动）
    c.execute("""
        INSERT OR REPLACE INTO essay_records
        (submission_id, student_id, student_name, assignment_id, exam_level, genre,
         topic_type, raw_content, raw_language, raw_total, display_total, grade,
         is_handwritten, graded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (submission_id, student_id, student_name, assignment_id, exam_level, genre,
          topic_type, raw_content, raw_language, raw_total, raw_total, grade,
          1 if is_handwritten else 0, now))

    # 2) error_tags：每个问题一行。先清掉这篇旧标签（重跑幂等），再插入
    c.execute("DELETE FROM error_tags WHERE submission_id = ?", (submission_id,))
    paragraphs = feedback.get("paragraph_feedback", []) or []
    for p in paragraphs:
        if not isinstance(p, dict):
            continue
        para_role = (p.get("para_role") or "").strip()
        for issue in (p.get("red_issues") or []):
            if not isinstance(issue, dict):
                continue
            cat = _normalize_error_category(issue.get("type"), "red")
            detail = issue.get("issue_detail") or issue.get("explanation") or issue.get("original") or ""
            c.execute("""INSERT INTO error_tags
                (submission_id, student_id, error_category, severity, para_role, detail, graded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (submission_id, student_id, cat, ERROR_CATEGORIES.get(cat, "red"),
                 para_role, str(detail)[:300], now))
        for issue in (p.get("green_issues") or []):
            if not isinstance(issue, dict):
                continue
            cat = _normalize_error_category(issue.get("type"), "green")
            detail = issue.get("issue_detail") or issue.get("suggestion") or issue.get("original") or ""
            c.execute("""INSERT INTO error_tags
                (submission_id, student_id, error_category, severity, para_role, detail, graded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (submission_id, student_id, cat, ERROR_CATEGORIES.get(cat, "green"),
                 para_role, str(detail)[:300], now))


# ════════════════════════════════════════════════════════════════════
# 成长档案：查询函数（进步可视化靠这些实时算，不存快照）
# ════════════════════════════════════════════════════════════════════

def get_student_records(student_id, genre=None, exam_level=None, handwritten_only=None):
    """某学生的全部作文记录，按时间正序。用于画分数/能力曲线。
    handwritten_only=True 只取手写，=False 只取打字，=None 全取（隔离 OCR 噪音）。"""
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM essay_records WHERE student_id = ?"
    args = [student_id]
    if genre:
        q += " AND genre = ?"; args.append(genre)
    if exam_level:
        q += " AND exam_level = ?"; args.append(exam_level)
    if handwritten_only is True:
        q += " AND is_handwritten = 1"
    elif handwritten_only is False:
        q += " AND is_handwritten = 0"
    q += " ORDER BY graded_at ASC"
    c.execute(q, args)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_progress_summary(student_id):
    """进步可视化核心：本次 vs 上次的对比。实时算，不存死。
    返回 None（不足两篇）或一个含分数变化/错误数变化/各类问题增减的 dict。"""
    records = get_student_records(student_id)
    conn = get_conn()
    c = conn.cursor()

    def err_count(sub_id):
        c.execute("SELECT COUNT(*) AS n FROM error_tags WHERE submission_id = ?", (sub_id,))
        return c.fetchone()["n"]

    def err_by_cat(sub_id):
        c.execute("""SELECT error_category, COUNT(*) AS n FROM error_tags
                     WHERE submission_id = ? GROUP BY error_category""", (sub_id,))
        return {r["error_category"]: r["n"] for r in c.fetchall()}

    summary = {
        "total_essays": len(records),
        "has_comparison": len(records) >= 2,
    }
    if len(records) >= 1:
        latest = records[-1]
        summary["latest_total"] = latest["display_total"]
        summary["latest_grade"] = latest["grade"]
        summary["latest_errors"] = err_count(latest["submission_id"])
    if len(records) >= 2:
        latest, prev = records[-1], records[-2]
        # 分数变化只在同文体之间比才有意义；这里给原始差，前端按需过滤
        st_now = latest["display_total"] or 0
        st_prev = prev["display_total"] or 0
        summary["score_delta"] = st_now - st_prev
        e_now = err_count(latest["submission_id"])
        e_prev = err_count(prev["submission_id"])
        summary["error_delta"] = e_now - e_prev  # 负数 = 错误减少 = 进步
        cat_now = err_by_cat(latest["submission_id"])
        cat_prev = err_by_cat(prev["submission_id"])
        improved, worsened = [], []
        for cat in set(list(cat_now) + list(cat_prev)):
            d = cat_now.get(cat, 0) - cat_prev.get(cat, 0)
            if d < 0: improved.append((cat, d))
            elif d > 0: worsened.append((cat, d))
        summary["improved_categories"] = sorted(improved, key=lambda x: x[1])
        summary["worsened_categories"] = sorted(worsened, key=lambda x: -x[1])
    conn.close()
    return summary


def get_error_ranking(student_id, limit=10):
    """高频问题排行榜：某学生历来最常犯的问题类型。用于个性化训练。"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT error_category, severity, COUNT(*) AS freq
                 FROM error_tags WHERE student_id = ?
                 GROUP BY error_category ORDER BY freq DESC LIMIT ?""",
              (student_id, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def backfill_growth_data():
    """一次性回填：扫描全部历史 submissions，从 feedback_json 重建两张新表。
    幂等，可重复跑。新表出 bug 或加字段后，跑这个就能从原始 JSON 重建。"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT s.id, s.student_id, s.student_name, s.feedback_json,
                        s.assignment_id, a.exam_level, a.genre
                 FROM submissions s LEFT JOIN assignments a ON s.assignment_id = a.id""")
    rows = c.fetchall()
    done = 0
    for r in rows:
        try:
            fb = json.loads(r["feedback_json"]) if r["feedback_json"] else None
        except (json.JSONDecodeError, TypeError):
            fb = None
        if not fb:
            continue
        assignment = {"id": r["assignment_id"], "exam_level": r["exam_level"], "genre": r["genre"]}
        extract_growth_data(conn, r["id"], r["student_id"], r["student_name"],
                            assignment, fb, is_handwritten=True)
        done += 1
    conn.commit()
    conn.close()
    return done



def save_assignment(title, exam_level, genre, prompt, requirements, rubric, focus_areas=None):
    conn = get_conn()
    c = conn.cursor()
    focus_json = json.dumps(focus_areas or [], ensure_ascii=False)
    c.execute("""
        INSERT INTO assignments (title, exam_level, genre, prompt, requirements, rubric, focus_areas, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (title, exam_level, genre, prompt, requirements, rubric, focus_json, datetime.now().isoformat()))
    assignment_id = c.lastrowid
    conn.commit()
    conn.close()
    return assignment_id

def get_active_assignments():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM assignments WHERE is_active=1 ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_assignments():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM assignments ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def toggle_assignment(assignment_id, is_active):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE assignments SET is_active=? WHERE id=?", (is_active, assignment_id))
    conn.commit()
    conn.close()

def delete_assignment(assignment_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM assignments WHERE id=?", (assignment_id,))
    conn.commit()
    conn.close()

def save_submission(assignment_id, student_id, student_name, image_bytes, ocr_text,
                    feedback_json, assignment=None, is_handwritten=True):
    """存提交。新增可选参数 assignment（dict，含 exam_level/genre/id）与 is_handwritten，
    用于同步提取成长档案数据。不传也能正常工作（向后兼容），只是少了 exam_level/genre。"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO submissions (assignment_id, student_id, student_name, submitted_at, image_data, ocr_text, feedback_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, student_id, student_name, datetime.now().isoformat(),
          image_bytes, ocr_text, json.dumps(feedback_json, ensure_ascii=False)))
    sid = c.lastrowid

    # 同步提取成长档案数据。提取失败绝不能拖垮主流程（存提交是第一要务）
    try:
        asgn = assignment or {"id": assignment_id}
        extract_growth_data(conn, sid, student_id, student_name, asgn,
                            feedback_json, is_handwritten=is_handwritten)
    except Exception:
        pass  # 提取失败静默跳过，事后可用 backfill_growth_data() 重建

    conn.commit()
    conn.close()
    return sid

def get_all_submissions():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, a.title as assignment_title, a.genre
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        ORDER BY s.submitted_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_submissions_for_assignment(assignment_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, a.title as assignment_title
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        WHERE s.assignment_id = ?
        ORDER BY s.submitted_at DESC
    """, (assignment_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_viewed(submission_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE submissions SET viewed_at=? WHERE id=? AND viewed_at IS NULL",
              (datetime.now().isoformat(), submission_id))
    conn.commit()
    conn.close()

init_db()
