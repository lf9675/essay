import streamlit as st

st.set_page_config(
    page_title="华文作文批改平台",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── 全局样式 ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500;600&display=swap');

* { font-family: 'Noto Sans SC', sans-serif; }
h1, h2, h3, h4 { font-family: 'Noto Serif SC', serif; }

/* 隐藏 Streamlit 默认侧边栏 */
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebarUserContent"] { display: none; }

/* 主体 */
.main { background: #faf8f5; }
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

/* ── 顶部品牌栏 + 导航 ── */
.top-bar {
    background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
    border-radius: 12px;
    padding: 0.9rem 1.5rem;
    margin-bottom: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.brand {
    color: #f0c27f;
    font-family: 'Noto Serif SC', serif;
    font-size: 1.15rem;
    font-weight: 700;
}
.brand-sub {
    color: #b8c5d6;
    font-size: 0.8rem;
    margin-left: 0.5rem;
}

/* ── 导航按钮组(用 stButton 模拟) ── */
.nav-button-row .stButton > button {
    background: transparent;
    color: white;
    border: 1px solid rgba(240,194,127,0.4);
    border-radius: 8px;
    padding: 0.4rem 1rem;
    font-size: 0.9rem;
    font-weight: 500;
    width: 100%;
    height: 40px;
    transition: all 0.2s;
}
.nav-button-row .stButton > button:hover {
    background: rgba(240,194,127,0.15);
    border-color: #f0c27f;
    color: #f0c27f;
    transform: none;
    box-shadow: none;
}

/* ── 首页内容卡片 ── */
.welcome-card {
    background: white;
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    border: 1px solid #e8e0d5;
    text-align: center;
}
.welcome-card h2 {
    color: #1a1a2e;
    font-size: 1.5rem;
    margin: 0 0 0.4rem 0;
}
.welcome-card p {
    color: #666;
    font-size: 0.95rem;
    margin: 0;
}

/* ── 功能卡片(下方备份入口) ── */
.feature-card {
    background: white;
    border-radius: 14px;
    padding: 1.5rem;
    text-align: center;
    border: 1px solid #e8e0d5;
    transition: all 0.3s;
    height: 170px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.feature-card:hover {
    border-color: #0f3460;
    box-shadow: 0 6px 24px rgba(15,52,96,0.12);
    transform: translateY(-3px);
}
.feature-icon { font-size: 2.2rem; margin-bottom: 0.6rem; }
.feature-title {
    font-family: 'Noto Serif SC', serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 0.3rem;
}
.feature-desc {
    color: #888;
    font-size: 0.82rem;
    line-height: 1.5;
}

/* ── 主按钮(深色) ── */
.main-btn-row .stButton > button {
    background: linear-gradient(135deg, #0f3460, #16213e);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.7rem 2rem;
    font-size: 0.95rem;
    font-weight: 500;
    width: 100%;
}
.main-btn-row .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(15,52,96,0.3);
}

/* ── 信息条 ── */
.info-strip {
    background: #fdf8ee;
    border-left: 3px solid #f0c27f;
    border-radius: 6px;
    padding: 0.6rem 1rem;
    margin-bottom: 1.5rem;
    font-size: 0.88rem;
    color: #5d3700;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# 顶部品牌栏 + 横向导航按钮
# ══════════════════════════════════════════════════════════
st.markdown("""
<div class="top-bar">
    <div>
        <span class="brand">📝 华文作文批改平台</span>
        <span class="brand-sub">SEAB 评分标准 · AI 智能批改</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 横向导航按钮
st.markdown('<div class="nav-button-row">', unsafe_allow_html=True)
nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
with nav_col1:
    st.button("🏠 首页", key="nav_home", disabled=True)
with nav_col2:
    if st.button("🎓 学生作文提交", key="nav_student"):
        st.switch_page("pages/student.py")
with nav_col3:
    if st.button("👩‍🏫 教师管理后台", key="nav_admin"):
        st.switch_page("pages/admin.py")
with nav_col4:
    if st.button("📈 学生进步追踪", key="nav_progress"):
        st.switch_page("pages/progress.py")
st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# 欢迎信息(简洁,不占太多空间)
# ══════════════════════════════════════════════════════════
st.markdown("""
<div class="welcome-card">
    <h2>欢迎使用华文作文批改平台</h2>
    <p>新加坡中学华文 / 高级华文 · 基于考评局官方评分标准的 AI 段落式专业批改</p>
</div>
""", unsafe_allow_html=True)

# 信息条 — 简短特性介绍
st.markdown("""
<div class="info-strip">
    💡 <strong>本系统特色：</strong>
    嵌入 SEAB 官方评分标准 · 段落式逐段批改 · 基础版 + 进阶版双层修改示范 · 教练式建议
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# 三个功能卡片(下方备份入口)
# ══════════════════════════════════════════════════════════
st.markdown('<div class="main-btn-row">', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🎓</div>
        <div class="feature-title">学生作文提交</div>
        <div class="feature-desc">提交作文,获得段落式专业批改</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("进入学生页面", key="student_btn"):
        st.switch_page("pages/student.py")

with col2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">👩‍🏫</div>
        <div class="feature-title">教师管理后台</div>
        <div class="feature-desc">设置题目,查看学生提交记录</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("进入教师后台", key="admin_btn"):
        st.switch_page("pages/admin.py")

with col3:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📈</div>
        <div class="feature-title">学生进步追踪</div>
        <div class="feature-desc">查看历次提交,跟踪进步轨迹</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("进入进步追踪", key="progress_btn"):
        st.switch_page("pages/progress.py")
st.markdown('</div>', unsafe_allow_html=True)
