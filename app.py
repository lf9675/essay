import streamlit as st

st.set_page_config(
    page_title="华文作文批改平台",
    page_icon="📝",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500&display=swap');

* { font-family: 'Noto Sans SC', sans-serif; }
h1, h2, h3 { font-family: 'Noto Serif SC', serif; }

.main { background: #faf8f5; }

.hero-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 20px;
    padding: 3rem;
    text-align: center;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.hero-card h1 { color: #f0c27f; font-size: 2.5rem; margin-bottom: 0.5rem; }
.hero-card p { color: #b8c5d6; font-size: 1.1rem; }

.nav-card {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    border: 2px solid #e8e0d5;
    cursor: pointer;
    transition: all 0.3s ease;
    height: 200px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.nav-card:hover { border-color: #0f3460; box-shadow: 0 8px 30px rgba(15,52,96,0.15); transform: translateY(-4px); }
.nav-icon { font-size: 3rem; margin-bottom: 1rem; }
.nav-title { font-family: 'Noto Serif SC', serif; font-size: 1.3rem; font-weight: 700; color: #1a1a2e; }
.nav-desc { color: #888; font-size: 0.9rem; margin-top: 0.3rem; }

.stButton > button {
    background: linear-gradient(135deg, #0f3460, #16213e);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.7rem 2rem;
    font-family: 'Noto Sans SC', sans-serif;
    font-size: 1rem;
    font-weight: 500;
    width: 100%;
    transition: all 0.3s ease;
}
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(15,52,96,0.3); }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-card">
    <h1>📝 华文作文批改平台</h1>
    <p>新加坡中学高级华文 · AI 辅助批改系统</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap="large")

with col1:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-icon">🎓</div>
        <div class="nav-title">学生作文提交</div>
        <div class="nav-desc">上传作文照片，获取即时批改反馈</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("进入学生页面", key="student_btn"):
        st.switch_page("pages/student.py")

with col2:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-icon">👩‍🏫</div>
        <div class="nav-title">教师管理后台</div>
        <div class="nav-desc">设置题目标准，查看批改记录</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("进入教师后台", key="admin_btn"):
        st.switch_page("pages/admin.py")

with col3:
    st.markdown("""
    <div class="nav-card">
        <div class="nav-icon">📈</div>
        <div class="nav-title">学生进步追踪</div>
        <div class="nav-desc">查看学生历次提交的分数变化</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("进入进步追踪", key="progress_btn"):
        st.switch_page("pages/progress.py")
