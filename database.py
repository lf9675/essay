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


def get_progress_card_data(student_id, current_submission_id):
    """为“进步卡片”准备数据。核心是：分数只跟【同文体的上一篇】比，
    避免记叙文跟议论文比分这种误导。返回一个 dict，前端按 state 渲染。

    state 三选一：
      'first'    第一篇（同文体没有更早的可比对象）
      'progress' 比同文体上一篇进步（分数涨 或 错误减少）
      'attention'其他（分数没涨/退步），转成温和提醒，不打击

    返回字段：
      state, score, max_score, grade,
      score_delta (None=无同文体可比), 
      top_issue (最常见问题，个性化训练入口；None=暂无),
      improved_note (进步点的人话描述), headline (一句老师的话)
    """
    conn = get_conn()
    c = conn.cursor()

    # 当前这篇
    c.execute("SELECT * FROM essay_records WHERE submission_id = ?", (current_submission_id,))
    cur = c.fetchone()
    if not cur:
        conn.close()
        return None
    cur = dict(cur)
    genre = cur.get("genre") or ""

    # 找【同文体】里时间更早的最近一篇（同学生，排除自己）
    c.execute("""SELECT * FROM essay_records
                 WHERE student_id = ? AND genre = ? AND submission_id != ?
                   AND graded_at < ?
                 ORDER BY graded_at DESC LIMIT 1""",
              (student_id, genre, current_submission_id, cur.get("graded_at") or ""))
    prev_row = c.fetchone()
    prev = dict(prev_row) if prev_row else None

    # 满分按考级取（HCL=60，其余 40）。essay_records 没存满分，从 exam_level 推。
    max_score = 60 if (cur.get("exam_level") == "HCL") else 40
    score = cur.get("display_total")
    grade = cur.get("grade") or ""

    # 当前这篇的错误数 + 最常见问题
    def err_count(sid):
        c.execute("SELECT COUNT(*) n FROM error_tags WHERE submission_id = ?", (sid,))
        return c.fetchone()["n"]
    cur_err = err_count(current_submission_id)

    # 最常见问题 = 该学生历来高频第一（个性化训练入口）
    c.execute("""SELECT error_category, COUNT(*) freq FROM error_tags
                 WHERE student_id = ? GROUP BY error_category
                 ORDER BY freq DESC LIMIT 1""", (student_id,))
    top_row = c.fetchone()
    top_issue = top_row["error_category"] if top_row else None

    data = {
        "score": score, "max_score": max_score, "grade": grade,
        "score_delta": None, "top_issue": top_issue,
        "improved_note": "", "headline": "",
    }

    if prev is None:
        # 第一篇（同文体无可比）
        data["state"] = "first"
        data["headline"] = "这是一个很好的起点！把这篇收好，下次再写一篇同类作文，我就能告诉你进步了多少。"
        conn.close()
        return data

    prev_err = err_count(prev["submission_id"])
    s_now = score or 0
    s_prev = prev.get("display_total") or 0
    delta = s_now - s_prev
    data["score_delta"] = delta

    # 找“改掉的问题”（上次有、这次没有的类别），拼人话
    def err_cats(sid):
        c.execute("""SELECT error_category, COUNT(*) n FROM error_tags
                     WHERE submission_id = ? GROUP BY error_category""", (sid,))
        return {r["error_category"]: r["n"] for r in c.fetchall()}
    now_cats = err_cats(current_submission_id)
    prev_cats = err_cats(prev["submission_id"])
    fixed = []
    for cat, n in prev_cats.items():
        reduced = n - now_cats.get(cat, 0)
        if reduced > 0:
            fixed.append((cat, reduced))
    fixed.sort(key=lambda x: -x[1])

    is_progress = (delta > 0) or (cur_err < prev_err)
    if is_progress:
        data["state"] = "progress"
        parts = []
        if delta > 0:
            parts.append(f"比上次{genre}进步了 {delta} 分")
        if fixed:
            cat, n = fixed[0]
            parts.append(f"{cat}的问题少了 {n} 个" if cat in ("错别字", "标点错误", "病句")
                         else f"{cat}的毛病改掉了")
        data["improved_note"] = "，".join(parts) if parts else "这次写得更稳了"
        data["headline"] = "继续保持！" + (
            f"下次特别留意一下「{top_issue}」，这是你最近最常遇到的。" if top_issue else "")
    else:
        data["state"] = "attention"
        data["headline"] = (
            f"这次的作文有它的亮点。下次只要重点改一个地方就好：留意「{top_issue}」，"
            "这是你最近最常遇到的问题。" if top_issue else
            "这次的作文有它的亮点，继续多练，慢慢就会更稳。")

    conn.close()
    return data


def render_progress_card_html(data):
    """把 get_progress_card_data 的返回渲染成 HTML 字符串。
    用 st.markdown(html, unsafe_allow_html=True) 输出。数据与展示分离，
    调文案只改 get_progress_card_data，调样式只改这里。
    设计原则：单一主色、不堆术语、退步不打击、最常见问题作为训练入口。"""
    if not data:
        return ""

    state = data.get("state")
    score = data.get("score")
    max_score = data.get("max_score", 60)
    grade = data.get("grade") or ""
    delta = data.get("score_delta")
    top_issue = data.get("top_issue")
    improved = data.get("improved_note") or ""
    headline = data.get("headline") or ""

    grade_str = f" · {grade}" if grade else ""
    score_str = f"{score}" if score is not None else "—"

    # 主色 + 图标 + 标题，按状态切换（退步用中性蓝，不用红）
    if state == "progress":
        accent = "#1D9E75"; icon = "&#9650;"; title = "这次比上次进步了"
    elif state == "attention":
        accent = "#185FA5"; icon = "&#9873;"; title = "这次有几个地方可以再注意"
    else:  # first
        accent = "#1D9E75"; icon = "&#10022;"; title = "这是你的第一篇作文"

    # 右侧第二格内容按状态变化
    if state == "progress" and delta is not None:
        right_label = "比上次同类作文"
        right_value = f'<span style="color:{accent}">{"+" if delta>=0 else ""}{delta} 分</span>'
        right_sub = ""
    elif top_issue:
        right_label = "最常出现的问题"
        right_value = f'{top_issue}'
        right_sub = "点这里多练这一类"  # 预留训练入口，暂为提示文案
    else:
        right_label = "这次发现"
        right_value = f'{score is not None and "几处" or "—"}'
        right_sub = "可以改进的地方"

    # 进步状态额外显示“改掉了什么”
    improved_html = (
        f'<div style="font-size:14px;line-height:1.7;color:#1a1a1a;margin-bottom:6px">'
        f'<span style="color:{accent};font-weight:500">{improved}</span>。</div>'
        if (state == "progress" and improved) else ""
    )

    # 最常见问题作为训练入口：预留 data-* 钩子，未来接专项训练时用 JS/Streamlit 捕获
    issue_hook = (
        f' data-train-issue="{top_issue}"' if top_issue else ""
    )

    html = f"""
<div style="background:#fff;border:0.5px solid rgba(0,0,0,0.12);border-radius:12px;padding:16px 20px;margin:8px 0 16px"{issue_hook}>
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
    <span style="font-size:20px;color:{accent}">{icon}</span>
    <span style="font-size:16px;font-weight:500;color:#1a1a1a">{title}</span>
  </div>
  <div style="display:flex;gap:10px;margin-bottom:12px">
    <div style="flex:1;background:#f5f4ef;border-radius:8px;padding:10px 12px">
      <div style="font-size:13px;color:#6b6a64">这次得分</div>
      <div style="font-size:24px;font-weight:500;color:#1a1a1a">{score_str} <span style="font-size:14px;color:#6b6a64">/ {max_score}{grade_str}</span></div>
    </div>
    <div style="flex:1;background:#f5f4ef;border-radius:8px;padding:10px 12px">
      <div style="font-size:13px;color:#6b6a64">{right_label}</div>
      <div style="font-size:20px;font-weight:500;color:#1a1a1a;padding-top:2px">{right_value}</div>
      {f'<div style="font-size:13px;color:#6b6a64">{right_sub}</div>' if right_sub else ''}
    </div>
  </div>
  {improved_html}
  <div style="font-size:14px;line-height:1.7;color:#1a1a1a">{headline}</div>
</div>
"""
    return html


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
