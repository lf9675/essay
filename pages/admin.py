import streamlit as st
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import (save_assignment, get_all_assignments, toggle_assignment,
                      delete_assignment, get_all_submissions)

st.set_page_config(page_title="教师管理后台", page_icon="👩‍🏫", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500&display=swap');
* { font-family: 'Noto Sans SC', sans-serif; }
h1,h2,h3,h4 { font-family: 'Noto Serif SC', serif; }
.main { background: #f5f7fa; }
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebarUserContent"] { display: none; }
.block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { background: transparent; }
.stApp > header { background: transparent; }

.page-header {
    background: linear-gradient(135deg, #1a1a2e, #0f3460);
    color: white; border-radius: 16px; padding: 1.5rem 2rem;
    margin-bottom: 1.5rem; display: flex; align-items: center; gap: 1rem;
}
.page-header h2 { color: #f0c27f; margin: 0; font-size: 1.6rem; }
.page-header p { color: #b8c5d6; margin: 0; font-size: 0.95rem; }

.card {
    background: white; border-radius: 16px; padding: 1.5rem;
    border: 1px solid #e0e7ef; margin-bottom: 1rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.card h3 { color: #1a1a2e; font-family: 'Noto Serif SC', serif; margin-bottom: 1rem; }

.stat-box {
    background: linear-gradient(135deg, #1a1a2e, #0f3460);
    border-radius: 12px; padding: 1.2rem; text-align: center; color: white;
}
.stat-num { font-size: 2.5rem; font-weight: 700; color: #f0c27f; }
.stat-label { color: #b8c5d6; font-size: 0.85rem; }

.focus-box {
    background: #f0f7ff; border: 1px solid #b3d4ff; border-radius: 12px;
    padding: 1rem 1.2rem; margin: 0.8rem 0;
}
.focus-box h4 { color: #0f3460; margin-bottom: 0.6rem; font-size: 0.95rem; }
.focus-tag {
    display: inline-block; background: #0f3460; color: white;
    border-radius: 20px; padding: 0.2rem 0.7rem; font-size: 0.78rem;
    margin: 0.2rem;
}

.active-badge { background: #e8f5e9; color: #2e7d32; border-radius: 4px; padding: 0.2rem 0.6rem; font-size: 0.78rem; font-weight: 600; }
.inactive-badge { background: #fce4ec; color: #c62828; border-radius: 4px; padding: 0.2rem 0.6rem; font-size: 0.78rem; font-weight: 600; }
.viewed-tag { background: #e8f5e9; color: #2e7d32; border-radius: 4px; padding: 0.15rem 0.5rem; font-size: 0.75rem; }
.not-viewed-tag { background: #fff3e0; color: #e65100; border-radius: 4px; padding: 0.15rem 0.5rem; font-size: 0.75rem; }

.radar-label { font-size: 0.78rem; color: #666; }

.level-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 0.5rem; }
.level-table th { background: #1a1a2e; color: #f0c27f; padding: 0.5rem 0.8rem; text-align: left; }
.level-table td { padding: 0.5rem 0.8rem; border-bottom: 1px solid #e0e7ef; vertical-align: top; }
.level-table tr:nth-child(even) td { background: #f8fafc; }
.orig-cell { color: #c62828; }
.mid-cell { color: #e65100; }
.best-cell { color: #2e7d32; font-weight: 500; }
.tip-cell { color: #6a1b9a; font-size: 0.78rem; }

.stButton > button {
    background: linear-gradient(135deg, #0f3460, #16213e);
    color: white; border: none; border-radius: 10px;
    padding: 0.6rem 1.5rem; font-family: 'Noto Sans SC', sans-serif;
    font-size: 0.95rem; width: 100%;
}
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(15,52,96,0.25); }
.stTextInput > div > div > input,
.stTextArea > div > div > textarea { border-radius: 10px; border-color: #e0e7ef; }
</style>
""", unsafe_allow_html=True)

# ── Password gate ──────────────────────────────────────────
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "teacher2024")
if 'admin_auth' not in st.session_state:
    st.session_state['admin_auth'] = False

if not st.session_state['admin_auth']:
    st.markdown("""
    <div class="page-header">
        <span style="font-size:2rem">👩‍🏫</span>
        <div><h2>教师管理后台</h2><p>请输入教师密码</p></div>
    </div>""", unsafe_allow_html=True)
    pw = st.text_input("教师密码", type="password")
    if st.button("登入"):
        if pw == ADMIN_PASSWORD:
            st.session_state['admin_auth'] = True
            st.rerun()
        else:
            st.error("密码错误，请重试。")
    st.stop()

# ── 顶部导航栏 ───────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1a1a2e,#0f3460);border-radius:12px;
    padding:0.9rem 1.5rem;margin-bottom:1rem;display:flex;justify-content:space-between;
    align-items:center;flex-wrap:wrap;gap:1rem;box-shadow:0 4px 16px rgba(0,0,0,0.08);">
    <div>
        <span style="color:#f0c27f;font-family:'Noto Serif SC',serif;font-size:1.15rem;font-weight:700;">
            CLever · 华文通
        </span>
        <span style="color:#b8c5d6;font-size:0.8rem;margin-left:0.5rem;">
            教师管理后台
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 横向导航按钮 ──
st.markdown("""<style>
.nav-row .stButton > button {
    background: transparent; color: #1a1a2e; border: 1px solid #e0e7ef;
    border-radius: 8px; padding: 0.4rem 1rem; font-size: 0.9rem;
    font-weight: 500; width: 100%; height: 40px; transition: all 0.2s;
}
.nav-row .stButton > button:hover {
    background: #f0f7ff; border-color: #1e88e5; color: #0f3460;
    transform: none; box-shadow: none;
}
</style><div class="nav-row">""", unsafe_allow_html=True)
nav1, nav2, nav3, nav4, nav5 = st.columns(5)
with nav1:
    if st.button("🏠 首页", key="nav_home_a"):
        st.switch_page("app.py")
with nav2:
    if st.button("🎓 学生作文提交", key="nav_student_a"):
        st.switch_page("pages/student.py")
with nav3:
    st.button("👩‍🏫 教师管理后台", key="nav_admin_a", disabled=True)
with nav4:
    if st.button("📈 学生进步追踪", key="nav_progress_a"):
        st.switch_page("pages/progress.py")
with nav5:
    if st.button("🚪 登出", key="nav_logout_a"):
        st.session_state['admin_auth'] = False
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Stats ───────────────────────────────────────────────────
all_assignments = get_all_assignments()
all_submissions = get_all_submissions()
active_count = sum(1 for a in all_assignments if a['is_active'])
viewed_count = sum(1 for s in all_submissions if s['viewed_at'])
unviewed_count = len(all_submissions) - viewed_count

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-box"><div class="stat-num">{len(all_assignments)}</div><div class="stat-label">作文题目总数</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-box"><div class="stat-num">{active_count}</div><div class="stat-label">开放中题目</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-box"><div class="stat-num">{len(all_submissions)}</div><div class="stat-label">学生提交总数</div></div>', unsafe_allow_html=True)
with c4:
    color = "#e53935" if unviewed_count > 0 else "#f0c27f"
    st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:{color}">{unviewed_count}</div><div class="stat-label">未查看批改</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 考试段定义（从 prompts.py 同步）────────────────────────────
EXAM_LEVELS_UI = {
    "HCL": "中学高级华文 (HCL) — 60分制",
    "O_CL": "中学普通华文 O水准 (CL 1160) — 40分制",
    "N_CL": "中学普通华文 N水准 (CL 1196) — 40分制",
    "PRACTICAL_O": "中学实用文 O水准 — 20分制",
    "PRACTICAL_N": "中学实用文 N水准 — 20分制",
}

# ── 文体选项（按考试段过滤）─────────────────────────────────
GENRES_BY_LEVEL = {
    "HCL": ["记叙文", "议论文", "说明文"],
    "O_CL": ["记叙文", "议论文", "说明文"],
    "N_CL": ["记叙文", "议论文", "说明文"],
    "PRACTICAL_O": ["电子邮件"],
    "PRACTICAL_N": ["电子邮件"],
}

# ── All focus area options by genre ────────────────────────
FOCUS_OPTIONS = {
    "记叙文": [
        "错别字与基础病句",
        "人物描写（语言/动作/心理/外貌）",
        "情节结构（开头/发展/高潮/结局）",
        "感官细节与场景描写",
        "开头与结尾的呼应",
        "过渡句与段落连贯性",
        "主题与情感表达",
    ],
    "议论文": [
        "错别字与基础病句",
        "论点是否清晰",
        "论据是否充分有力",
        "论证逻辑（推理过程）",
        "段落结构（PEEL）",
        "开头的立场陈述",
        "结尾的总结升华",
    ],
    "说明文": [
        "错别字与基础病句",
        "说明顺序是否清晰",
        "说明方法的运用",
        "语言准确性与客观性",
        "段落组织",
    ],
    "电子邮件": [
        "错别字与基础病句",
        "格式是否正确（称谓/日期/署名）",
        "语气是否得体",
        "内容是否切合情境",
        "分段与条理",
    ],
}

tab1, tab2, tab3 = st.tabs(["➕ 创建新题目", "📋 管理题目", "📊 学生提交记录"])

# ══════════════════════════════════════════════════════════
# TAB 1: Create Assignment
# ══════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="card"><h3>✏️ 创建新作文题目</h3>', unsafe_allow_html=True)

    # 第一行：考试段（最关键的选择，决定后续所有内容）
    exam_level = st.selectbox(
        "📚 考试段（决定评分标准）",
        list(EXAM_LEVELS_UI.keys()),
        format_func=lambda k: EXAM_LEVELS_UI[k],
        help="系统会自动套用对应的 SEAB 官方评分标准，无需手动输入 rubric"
    )

    # 显示当前考试段的官方信息
    level_info = {
        "HCL": ("60", "500", "内容(30) + 语文(30)"),
        "O_CL": ("40", "300", "内容(20) + 语文(20)"),
        "N_CL": ("40", "240", "内容(20) + 语文(20)"),
        "PRACTICAL_O": ("20", "150", "内容(10) + 语文(10)"),
        "PRACTICAL_N": ("20", "120", "内容(10) + 语文(10)"),
    }
    total, min_words, breakdown = level_info[exam_level]
    st.info(f"📋 **{EXAM_LEVELS_UI[exam_level]}**　总分 **{total}**　字数要求 **{min_words}+ 字**　评分维度：{breakdown}")

    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("题目名称（供老师识别用）", placeholder="例如：HCL 期中考 1 - 论手机利弊")
    with col2:
        # 文体根据考试段动态变化
        available_genres = GENRES_BY_LEVEL.get(exam_level, ["记叙文"])
        genre = st.selectbox("文体", available_genres)

    prompt = st.text_area("写作题目（学生看到的）", placeholder="例如：《第一次独立旅行》\n请以此为题，写一篇记叙文……", height=90)
    requirements = st.text_area("写作要求（选填）", placeholder=f"例如：字数不少于{min_words}字；必须有清晰的起伏情节；运用至少两种描写手法", height=70)

    # rubric 改成"补充说明"，因为官方标准已经自动嵌入
    rubric = st.text_area(
        "📝 老师补充说明（选填，附加在 SEAB 官方标准之后）",
        placeholder="例如：本次特别看重学生是否能结合个人经历，举出真实例子。\n如不填，AI 将完全按 SEAB 官方标准评分。",
        height=80,
        help="官方 SEAB 评分标准已自动嵌入，老师只需补充本次教学的特别要求即可"
    )

    # ── Focus area toggles ──────────────────────────────────
    st.markdown('<div class="focus-box"><h4>🎯 本次批改焦点（勾选需要重点批改的项目）</h4>', unsafe_allow_html=True)
    st.caption("只勾选本次课程重点，减少学生认知负荷。全不勾选 = AI按官方标准全面批改。")

    focus_opts = FOCUS_OPTIONS.get(genre, FOCUS_OPTIONS["记叙文"])
    selected_focus = []
    cols = st.columns(2)
    for i, opt in enumerate(focus_opts):
        with cols[i % 2]:
            if st.checkbox(opt, key=f"focus_{i}"):
                selected_focus.append(opt)

    if selected_focus:
        tags = "".join([f'<span class="focus-tag">✓ {f}</span>' for f in selected_focus])
        st.markdown(f"<p style='margin-top:0.5rem;'>已选：{tags}</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("💾 保存题目"):
        if not title or not prompt:
            st.error("请填写题目名称和写作题目。")
        else:
            aid = save_assignment(title, exam_level, genre, prompt, requirements, rubric, selected_focus)
            st.success(f"✅ 题目已保存！系统已套用 {EXAM_LEVELS_UI[exam_level]} 的官方评分标准。学生现在可以提交作文了。")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# TAB 2: Manage Assignments
# ══════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="card"><h3>📋 所有作文题目</h3>', unsafe_allow_html=True)
    if not all_assignments:
        st.info("还没有创建任何题目。")
    else:
        for a in all_assignments:
            badge = '<span class="active-badge">✅ 开放中</span>' if a['is_active'] else '<span class="inactive-badge">⏸ 已关闭</span>'
            sub_count = sum(1 for s in all_submissions if s['assignment_id'] == a['id'])
            with st.expander(f"📝 {a['title']} — {a['genre']}  {badge}  ({sub_count}份提交)", expanded=False):
                st.markdown(f"**题目：** {a['prompt']}")
                if a.get('requirements'):
                    st.markdown(f"**要求：** {a['requirements']}")

                # Show focus areas
                try:
                    focus_list = json.loads(a.get('focus_areas') or '[]')
                except:
                    focus_list = []
                if focus_list:
                    tags = "".join([f'<span class="focus-tag">✓ {f}</span>' for f in focus_list])
                    st.markdown(f"**批改焦点：** {tags}", unsafe_allow_html=True)
                else:
                    st.caption("批改焦点：全维度（未设定）")

                st.caption(f"创建时间：{a['created_at'][:16] if a['created_at'] else '—'}")
                col_a, col_b = st.columns(2)
                with col_a:
                    label = "⏸ 关闭题目" if a['is_active'] else "✅ 重新开放"
                    if st.button(label, key=f"toggle_{a['id']}"):
                        toggle_assignment(a['id'], 0 if a['is_active'] else 1)
                        st.rerun()
                with col_b:
                    if st.button("🗑️ 删除题目", key=f"del_{a['id']}"):
                        delete_assignment(a['id'])
                        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# TAB 3: Submissions
# ══════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="card"><h3>📊 学生提交记录</h3>', unsafe_allow_html=True)

    if not all_submissions:
        st.info("还没有学生提交作文。")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            assignment_filter_options = ["全部题目"] + list(dict.fromkeys(s['assignment_title'] for s in all_submissions))
            filter_choice = st.selectbox("筛选题目", assignment_filter_options)
        with col_f2:
            view_filter = st.radio("查看状态", ["全部", "未查看", "已查看"], horizontal=True)

        filtered = all_submissions if filter_choice == "全部题目" else [s for s in all_submissions if s['assignment_title'] == filter_choice]
        if view_filter == "未查看":
            filtered = [s for s in filtered if not s['viewed_at']]
        elif view_filter == "已查看":
            filtered = [s for s in filtered if s['viewed_at']]

        st.caption(f"显示 {len(filtered)} 份提交")

        for sub in filtered:
            viewed_html = '<span class="viewed-tag">✅ 已查看</span>' if sub['viewed_at'] else '<span class="not-viewed-tag">⚠️ 未查看</span>'
            submitted_time = sub['submitted_at'][:16] if sub['submitted_at'] else '—'

            with st.expander(f"👤 {sub['student_name']} ({sub['student_id']})  —  {sub['assignment_title']}  {viewed_html}  {submitted_time}", expanded=False):

                col_img, col_fb = st.columns([1, 2])

                with col_img:
                    if sub.get('image_data'):
                        st.image(sub['image_data'], caption="学生作文原图", use_column_width=True)
                    if sub.get('ocr_text'):
                        with st.expander("📄 OCR识别文字"):
                            st.text(sub['ocr_text'])

                with col_fb:
                    if sub.get('feedback_json'):
                        try:
                            fb = json.loads(sub['feedback_json'])
                        except:
                            fb = {}

                        # Radar scores
                        scores = fb.get('scores', {})
                        if scores:
                            try:
                                import plotly.graph_objects as go
                                dims = list(scores.keys())
                                vals = list(scores.values())
                                vals_closed = vals + [vals[0]]
                                dims_closed = dims + [dims[0]]
                                fig = go.Figure(go.Scatterpolar(
                                    r=vals_closed, theta=dims_closed,
                                    fill='toself',
                                    fillcolor='rgba(15,52,96,0.15)',
                                    line=dict(color='#0f3460', width=2),
                                    marker=dict(size=6, color='#f0c27f')
                                ))
                                fig.update_layout(
                                    polar=dict(radialaxis=dict(visible=True, range=[0,10])),
                                    showlegend=False, height=280, margin=dict(l=30,r=30,t=30,b=30),
                                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            except:
                                pass

                        # Strengths
                        strengths = fb.get('strengths', [])
                        if strengths:
                            st.markdown("**✅ 优点**")
                            for s in strengths: st.markdown(f"- {s}")

                        # Upgrade table
                        upgrades = fb.get('upgrade_table', [])
                        if upgrades:
                            st.markdown("**⬆️ 升级改写**")
                            rows_html = ""
                            for u in upgrades:
                                rows_html += f"""<tr>
                                    <td class="orig-cell">{u.get('original','')}</td>
                                    <td class="mid-cell">{u.get('level2','')}</td>
                                    <td class="best-cell">{u.get('level3','')}</td>
                                    <td class="tip-cell">{u.get('tip','')}</td>
                                </tr>"""
                            st.markdown(f"""
                            <table class="level-table">
                                <tr><th>原句</th><th>及格版</th><th>优秀版 ⭐</th><th>升级秘籍</th></tr>
                                {rows_html}
                            </table>""", unsafe_allow_html=True)

                        overall = fb.get('overall_suggestion', '')
                        if overall:
                            st.markdown(f"**🎯 总建议：** {overall}")

                        viewed_time = sub['viewed_at'][:16] if sub['viewed_at'] else '尚未查看'
                        st.caption(f"查看批改时间：{viewed_time}")

    st.markdown('</div>', unsafe_allow_html=True)
