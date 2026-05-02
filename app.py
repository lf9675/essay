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

/* 隐藏 Streamlit 默认侧边栏导航 */
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebarUserContent"] { display: none; }

/* 主体背景 */
.main { background: #faf8f5; }
.block-container { padding-top: 1rem; max-width: 1400px; }

/* ── 顶部导航栏 ── */
.top-nav {
    background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
    border-radius: 16px;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}
.nav-brand {
    color: #f0c27f;
    font-family: 'Noto Serif SC', serif;
    font-size: 1.3rem;
    font-weight: 700;
}
.nav-brand-sub {
    color: #b8c5d6;
    font-size: 0.85rem;
    margin-left: 0.6rem;
}

/* ── Hero card ── */
.hero-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 20px;
    padding: 2.5rem 2rem;
    text-align: center;
    color: white;
    margin-bottom: 1.5rem;
}
.hero-card h1 {
    color: #f0c27f;
    font-size: 2.2rem;
    margin-bottom: 0.3rem;
    font-weight: 700;
}
.hero-card p {
    color: #b8c5d6;
    font-size: 1rem;
    margin: 0;
}

/* ── 功能卡片 ── */
.nav-card {
    background: white;
    border-radius: 16px;
    padding: 1.8rem 1.5rem;
    text-align: center;
    border: 1px solid #e8e0d5;
    transition: all 0.3s ease;
    height: 180px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.nav-card:hover {
    border-color: #0f3460;
    box-shadow: 0 8px 30px rgba(15,52,96,0.15);
    transform: translateY(-4px);
}
.nav-icon { font-size: 2.5rem; margin-bottom: 0.8rem; }
.nav-title {
    font-family: 'Noto Serif SC', serif;
    font-size: 1.2rem;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 0.3rem;
}
.nav-desc {
    color: #888;
    font-size: 0.85rem;
    line-height: 1.5;
}

/* ── 按钮 ── */
.stButton > button {
    background: linear-gradient(135deg, #0f3460, #16213e);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.7rem 2rem;
    font-family: 'Noto Sans SC', sans-serif;
    font-size: 0.95rem;
    font-weight: 500;
    width: 100%;
    transition: all 0.3s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(15,52,96,0.3);
}
</style>
""", unsafe_allow_html=True)

# ── 顶部导航栏 ──
st.markdown("""
<div class="top-nav">
    <div>
        <span class="nav-brand">📝 华文作文批改平台</span>
        <span class="nav-brand-sub">SEAB 评分标准 · AI 智能批改</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Hero card ──
st.markdown("""
<div class="hero-card">
    <h1>欢迎使用</h1>
    <p>新加坡中学华文 / 高级华文 · 基于考评局官方评分标准的 AI 批改</p>
</div>
""", unsafe_allow_html=True)

# ── 三个功能卡片 ──
col1, col2, col3 = st.columns(3, gap="large")

with col1:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-icon">🎓</div>
        <div class="nav-title">学生作文提交</div>
        <div class="nav-desc">提交作文,获得段落式专业批改</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("进入学生页面", key="student_btn"):
        st.switch_page("pages/student.py")

with col2:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-icon">👩‍🏫</div>
        <div class="nav-title">教师管理后台</div>
        <div class="nav-desc">设置题目,查看学生提交记录</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("进入教师后台", key="admin_btn"):
        st.switch_page("pages/admin.py")

with col3:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-icon">📈</div>
        <div class="nav-title">学生进步追踪</div>
        <div class="nav-desc">查看历次提交,跟踪进步轨迹</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("进入进步追踪", key="progress_btn"):
        st.switch_page("pages/progress.py")
