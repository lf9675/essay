import streamlit as st
import json
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_all_submissions, get_all_assignments

st.set_page_config(page_title="学生进步追踪", page_icon="📈", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500&display=swap');
* { font-family: 'Noto Sans SC', sans-serif; }
h1,h2,h3 { font-family: 'Noto Serif SC', serif; }
.main { background: #f5f7fa; }
.page-header {
    background: linear-gradient(135deg, #1a1a2e, #0f3460);
    color: white; border-radius: 16px; padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
}
.page-header h2 { color: #f0c27f; margin: 0; font-size: 1.6rem; }
.page-header p { color: #b8c5d6; margin: 0.3rem 0 0 0; font-size: 0.95rem; }
.card {
    background: white; border-radius: 16px; padding: 1.5rem;
    border: 1px solid #e0e7ef; margin-bottom: 1rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.stat-box {
    background: linear-gradient(135deg, #1a1a2e, #0f3460);
    border-radius: 12px; padding: 1rem; text-align: center; color: white;
}
.stat-num { font-size: 2rem; font-weight: 700; color: #f0c27f; }
.stat-label { color: #b8c5d6; font-size: 0.82rem; margin-top: 0.2rem; }
.grade-badge {
    display: inline-block; border-radius: 8px; padding: 0.3rem 0.8rem;
    font-weight: 700; font-size: 1.1rem; margin: 0.2rem;
}
.stButton > button {
    background: linear-gradient(135deg, #0f3460, #16213e);
    color: white; border: none; border-radius: 10px;
    padding: 0.6rem 1.5rem; width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ── 密码验证 ──────────────────────────────────────────────
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "teacher2024")
if 'progress_auth' not in st.session_state:
    st.session_state['progress_auth'] = False

if not st.session_state['progress_auth']:
    st.markdown("""
    <div class="page-header">
        <h2>📈 学生进步追踪</h2>
        <p>请输入教师密码</p>
    </div>""", unsafe_allow_html=True)
    pw = st.text_input("密码", type="password")
    if st.button("登入"):
        if pw == ADMIN_PASSWORD:
            st.session_state['progress_auth'] = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

st.markdown("""
<div class="page-header">
    <h2>📈 学生进步追踪</h2>
    <p>根据学号和姓名追踪同一学生多次提交的分数变化</p>
</div>""", unsafe_allow_html=True)

col_back, _ = st.columns([1, 5])
with col_back:
    if st.button("← 返回主页"):
        st.switch_page("app.py")

# ── 加载数据 ──────────────────────────────────────────────
all_submissions = get_all_submissions()

if not all_submissions:
    st.info("还没有学生提交记录。")
    st.stop()

# 提取所有学生列表（去重）
seen = set()
students = []
for sub in all_submissions:
    key = (sub.get('student_id',''), sub.get('student_name',''))
    if key not in seen and key[0]:
        seen.add(key)
        students.append(key)
students = sorted(students, key=lambda x: x[1])

# ── 班级整体概览 ─────────────────────────────────────────
st.markdown("### 📊 班级整体概览")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="stat-box"><div class="stat-num">{len(students)}</div><div class="stat-label">学生人数</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="stat-box"><div class="stat-num">{len(all_submissions)}</div><div class="stat-label">提交总次数</div></div>', unsafe_allow_html=True)
with col3:
    multi_sub = sum(1 for s in students if sum(1 for sub in all_submissions
        if sub.get('student_id') == s[0] and sub.get('student_name') == s[1]) > 1)
    st.markdown(f'<div class="stat-box"><div class="stat-num">{multi_sub}</div><div class="stat-label">有多次提交的学生</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 学生选择 ─────────────────────────────────────────────
st.markdown("### 🔍 查看个别学生进步曲线")
student_options = {f"{name}（{sid}）": (sid, name) for sid, name in students}
selected_label = st.selectbox("选择学生", list(student_options.keys()))
selected_sid, selected_name = student_options[selected_label]

# 取该学生所有提交，按时间排序
student_subs = [sub for sub in all_submissions
    if sub.get('student_id') == selected_sid
    and sub.get('student_name') == selected_name]
student_subs = sorted(student_subs, key=lambda x: x.get('submitted_at',''))

if not student_subs:
    st.info("该学生暂无提交记录。")
    st.stop()

# ── 提取每次的分数 ────────────────────────────────────────
records = []
for sub in student_subs:
    try:
        fb = json.loads(sub.get('feedback_json', '{}'))
        scores = fb.get('scores', {})
        grade = fb.get('grade_estimate', '')
        if scores:
            records.append({
                'date': sub.get('submitted_at','')[:10],
                'datetime': sub.get('submitted_at',''),
                'scores': scores,
                'grade': grade,
                'assignment': sub.get('assignment_title',''),
            })
    except:
        pass

if not records:
    st.info("该学生的提交记录暂无分数数据。")
    st.stop()

# ── 进步曲线图 ───────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f"**{selected_name}（{selected_sid}）的进步曲线**")
st.caption(f"共 {len(records)} 次提交")

if len(records) >= 2:
    try:
        import plotly.graph_objects as go

        # 收集所有维度
        all_dims = list(records[0]['scores'].keys())
        labels = [f"第{i+1}次\n{r['date']}" for i, r in enumerate(records)]

        fig = go.Figure()
        colors = ['#0f3460','#43a047','#f9a825','#e53935','#8e24aa']
        for di, dim in enumerate(all_dims):
            vals = [r['scores'].get(dim, 0) for r in records]
            fig.add_trace(go.Scatter(
                x=labels, y=vals,
                mode='lines+markers',
                name=dim,
                line=dict(color=colors[di % len(colors)], width=2.5),
                marker=dict(size=9, symbol='circle'),
            ))

        fig.update_layout(
            title=f"{selected_name} 各维度分数变化",
            yaxis=dict(range=[0,10], title="分数（0-10）"),
            xaxis=dict(title="提交次数"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=380,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(248,250,252,1)',
            margin=dict(l=40,r=20,t=60,b=40)
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.caption(f"图表暂时无法显示：{e}")
else:
    st.info("需要至少2次提交才能显示进步曲线。目前只有1次提交。")

st.markdown('</div>', unsafe_allow_html=True)

# ── 每次提交详情 ─────────────────────────────────────────
st.markdown("### 📋 历次提交详情")
for i, r in enumerate(records):
    grade = r.get('grade','')
    if grade.startswith('A'):
        grade_color = '#43a047'
    elif grade.startswith('B'):
        grade_color = '#f9a825'
    else:
        grade_color = '#e53935'

    with st.expander(f"第{i+1}次　{r['date']}　{r['assignment']}　等级：{grade}", expanded=(i==len(records)-1)):
        # 分数展示
        score_cols = st.columns(len(r['scores']))
        for ci, (dim, val) in enumerate(r['scores'].items()):
            with score_cols[ci]:
                st.markdown(f"""
                <div style="text-align:center;background:#f8fafc;border-radius:10px;
                    padding:0.6rem;border:1px solid #e0e7ef;">
                    <div style="font-size:0.75rem;color:#666;">{dim}</div>
                    <div style="font-size:1.6rem;font-weight:700;
                        color:#0f3460;">{val}</div>
                    <div style="font-size:0.65rem;color:#999;">/ 10</div>
                </div>""", unsafe_allow_html=True)

        # 和上次比较
        if i > 0:
            prev = records[i-1]
            st.markdown("<br>", unsafe_allow_html=True)
            changes = []
            for dim in r['scores']:
                curr_val = r['scores'].get(dim, 0)
                prev_val = prev['scores'].get(dim, 0)
                diff = curr_val - prev_val
                if diff > 0:
                    changes.append(f"<span style='color:#43a047'>▲ {dim} +{diff}</span>")
                elif diff < 0:
                    changes.append(f"<span style='color:#e53935'>▼ {dim} {diff}</span>")
                else:
                    changes.append(f"<span style='color:#999'>— {dim}</span>")
            st.markdown(
                f"与上次相比：{'　'.join(changes)}",
                unsafe_allow_html=True
            )

# ── 班级分数分布 ─────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 班级最新成绩分布")
grade_counts = {}
for s in students:
    sid, sname = s
    subs = sorted([sub for sub in all_submissions
        if sub.get('student_id')==sid and sub.get('student_name')==sname],
        key=lambda x: x.get('submitted_at',''))
    if subs:
        try:
            fb = json.loads(subs[-1].get('feedback_json','{}'))
            g = fb.get('grade_estimate','').strip()
            if g:
                grade_counts[g] = grade_counts.get(g, 0) + 1
        except:
            pass

if grade_counts:
    try:
        import plotly.graph_objects as go
        grade_order = ['A1','A2','B3','B4','C5','C6','S7','S8','U9']
        grades = [g for g in grade_order if g in grade_counts]
        counts = [grade_counts[g] for g in grades]
        colors_bar = ['#43a047','#66bb6a','#f9a825','#ffa726','#ef5350','#e53935','#bdbdbd','#9e9e9e','#757575']
        fig2 = go.Figure(go.Bar(
            x=grades, y=counts,
            marker_color=colors_bar[:len(grades)],
            text=counts, textposition='outside'
        ))
        fig2.update_layout(
            title="班级最新等级分布",
            yaxis=dict(title="人数"),
            height=300,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(248,250,252,1)',
            margin=dict(l=30,r=20,t=50,b=30)
        )
        st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.caption(f"图表暂时无法显示：{e}")
