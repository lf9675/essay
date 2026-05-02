import streamlit as st
import anthropic
import base64
import json
import sys
import os
import PIL.Image
import io
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_active_assignments, save_submission, mark_viewed
from prompts import build_grading_prompt, build_user_message, EXAM_LEVELS

st.set_page_config(page_title="学生作文提交", page_icon="✏️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500&display=swap');
* { font-family: 'Noto Sans SC', sans-serif; }
h1,h2,h3 { font-family: 'Noto Serif SC', serif; }
.main { background: #faf8f5; }

.page-header {
    background: linear-gradient(135deg, #1a1a2e, #0f3460);
    color: white; border-radius: 16px; padding: 1.5rem 2rem;
    margin-bottom: 1.5rem; display: flex; align-items: center; gap: 1rem;
}
.page-header h2 { color: #f0c27f; margin: 0; font-size: 1.6rem; }
.page-header p { color: #b8c5d6; margin: 0; font-size: 0.95rem; }

.card {
    background: white; border-radius: 16px; padding: 1.5rem;
    border: 1px solid #e8e0d5; margin-bottom: 1rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.step-badge {
    background: #0f3460; color: #f0c27f; border-radius: 50%;
    width: 28px; height: 28px; display: inline-flex;
    align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.9rem; margin-right: 0.5rem;
}
.assignment-badge {
    background: #f0c27f22; border: 1px solid #f0c27f;
    border-radius: 8px; padding: 0.8rem 1rem;
    color: #7a5c1e; font-size: 0.95rem; margin-bottom: 0.5rem;
}
.ocr-warning {
    background: #fff8e1; border: 1px solid #ffc107;
    border-radius: 8px; padding: 0.8rem 1rem; color: #7a5000;
    font-size: 0.9rem; margin-bottom: 0.8rem;
}
.feedback-section { border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; }
.strengths { background: #e8f5e9; border-left: 4px solid #43a047; }
.issues-lang { background: #fff3e0; border-left: 4px solid #fb8c00; }
.issues-struct { background: #e3f2fd; border-left: 4px solid #1e88e5; }
.issues-content { background: #fce4ec; border-left: 4px solid #e53935; }
.suggestions { background: #f3e5f5; border-left: 4px solid #8e24aa; }
.upgrade-section { background: #f9fbe7; border-left: 4px solid #c0ca33; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; }
.issue-item {
    background: white; border-radius: 8px; padding: 0.8rem;
    margin-bottom: 0.6rem; font-size: 0.92rem;
}
.location-tag {
    background: #1a1a2e; color: white; border-radius: 4px;
    padding: 0.1rem 0.5rem; font-size: 0.78rem; margin-right: 0.5rem;
}
.original { color: #c62828; text-decoration: line-through; }
.improved { color: #2e7d32; font-weight: 500; }
.level-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-top: 0.5rem; }
.level-table th { background: #1a1a2e; color: #f0c27f; padding: 0.5rem 0.7rem; text-align: left; font-size: 0.82rem; }
.level-table td { padding: 0.5rem 0.7rem; border-bottom: 1px solid #e8e0d5; vertical-align: top; }
.level-table tr:nth-child(even) td { background: #fafaf0; }
.orig-cell { color: #c62828; }
.mid-cell { color: #e65100; }
.best-cell { color: #2e7d32; font-weight: 500; }
.tip-cell { color: #6a1b9a; font-size: 0.78rem; background: #f3e5f5; border-radius: 4px; padding: 0.2rem 0.4rem; }
.stButton > button {
    background: linear-gradient(135deg, #0f3460, #16213e);
    color: white; border: none; border-radius: 10px;
    padding: 0.7rem 2rem; font-family: 'Noto Sans SC', sans-serif;
    font-size: 1rem; font-weight: 500; width: 100%;
}
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(15,52,96,0.3); }
.stTextInput > div > div > input { border-radius: 10px; border-color: #e8e0d5; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <span style="font-size:2rem">✏️</span>
    <div><h2>学生作文提交</h2><p>上传作文照片，获取即时批改反馈</p></div>
</div>""", unsafe_allow_html=True)

if st.button("← 返回主页"):
    st.switch_page("app.py")

assignments = get_active_assignments()
if not assignments:
    st.info("📢 目前没有开放中的作文题目，请联系老师。")
    st.stop()

# ═══════════════════════════════════════════════════════════
# STAGE 1 — Student info + upload
# ═══════════════════════════════════════════════════════════
if 'ocr_done' not in st.session_state:
    st.session_state['ocr_done'] = False
if 'feedback' not in st.session_state:
    st.session_state['feedback'] = None

if not st.session_state['ocr_done']:

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="step-badge">1</span> **填写你的资料**', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        student_id = st.text_input("学号", placeholder="例如：24S101A")
    with col2:
        student_name = st.text_input("姓名", placeholder="例如：陈明辉")

    assignment_options = {f"{a['title']} ({a['genre']})": a for a in assignments}
    selected_label = st.selectbox("选择作文题目", list(assignment_options.keys()))
    selected_assignment = assignment_options[selected_label]

    if selected_assignment:
        st.markdown(f'<div class="assignment-badge">📌 <strong>题目：</strong>{selected_assignment["prompt"]}</div>', unsafe_allow_html=True)
        if selected_assignment.get('requirements'):
            st.markdown(f'<div class="assignment-badge" style="background:#e3f2fd22;border-color:#1e88e5;color:#1a3a5c;">📋 <strong>写作要求：</strong>{selected_assignment["requirements"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 输入方式选择 ─────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="step-badge">2</span> **选择输入方式**', unsafe_allow_html=True)
    input_method = st.radio(
        "请选择：",
        ["📷 方式一：上传照片，系统自动识别", "✍️ 方式二：自己输入或粘贴文字（推荐）"],
        horizontal=False
    )
    st.markdown('</div>', unsafe_allow_html=True)

    uploaded_files = []
    manual_text = ""

    if "方式一" in input_method:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**📷 上传作文照片（可多张）**")
        st.caption("作文有几页就上传几张，系统会用AI识别文字，识别后可手动修改。")
        uploaded_files = st.file_uploader(
            "请上传作文照片（JPG / PNG，可同时选多张）",
            type=["jpg","jpeg","png"],
            accept_multiple_files=True
        )
        if uploaded_files:
            st.caption(f"已上传 {len(uploaded_files)} 张照片：")
            cols = st.columns(min(len(uploaded_files), 3))
            for i, f in enumerate(uploaded_files):
                with cols[i % 3]:
                    st.image(f, caption=f"第{i+1}页", use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**✍️ 输入或粘贴作文文字**")
        st.info("💡 推荐做法：先用豆包、文心一言等大模型识别你的作文照片，把识别好的文字复制过来粘贴在下面，准确率更高！")
        manual_text = st.text_area(
            "在这里输入或粘贴你的作文：",
            placeholder="请在这里输入你的作文全文……\n\n也可以先用豆包等工具识别手写照片，再把文字复制过来粘贴。",
            height=400,
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="step-badge">3</span> **选择语音反馈语言**', unsafe_allow_html=True)
    tts_lang = st.radio("批改结果将以你选择的语言朗读", ["普通话 (Mandarin)", "英语 (English)"], horizontal=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if "方式一" in input_method:
        can_submit = bool(student_id and student_name and uploaded_files)
        if not can_submit:
            st.warning("请填写学号、姓名，并上传作文照片。")
    else:
        can_submit = bool(student_id and student_name and manual_text.strip())
        if not can_submit:
            st.warning("请填写学号、姓名，并输入作文内容。")

    if "方式二" in input_method:
        if st.button("🚀 直接提交批改！", disabled=not can_submit):
            st.session_state['ocr_text'] = manual_text.strip()
            st.session_state['image_bytes'] = b''
            st.session_state['all_image_bytes'] = []
            st.session_state['all_image_names'] = []
            st.session_state['selected_assignment'] = selected_assignment
            st.session_state['student_id'] = student_id
            st.session_state['student_name'] = student_name
            st.session_state['tts_lang'] = tts_lang
            st.session_state['ocr_done'] = True
            st.rerun()

    if "方式一" in input_method and st.button("📷 识别作文文字（核对后才批改）", disabled=not can_submit):
        with st.spinner(f"正在识别 {len(uploaded_files)} 张照片的文字，请稍候……"):
            try:
                # Read all images
                all_image_bytes = [f.read() for f in uploaded_files]

                client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

                def get_media_type(filename):
                    ext = filename.split(".")[-1].lower()
                    return "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"

                if len(all_image_bytes) == 1:
                    b64 = base64.standard_b64encode(all_image_bytes[0]).decode()
                    mt = get_media_type(uploaded_files[0].name)
                    ocr_resp = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=3000,
                        messages=[{"role": "user", "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
                            {"type": "text", "text": "请把图片中学生的手写作文，逐字逐句准确转录成文字。保留原本的分段结构，用换行表示分段。只输出转录的文字，不要加任何说明或评语。"}
                        ]}]
                    )
                    ocr_text = ocr_resp.content[0].text.strip()
                else:
                    all_pages = []
                    for i, (img_bytes, img_file) in enumerate(zip(all_image_bytes, uploaded_files)):
                        b64 = base64.standard_b64encode(img_bytes).decode()
                        mt = get_media_type(img_file.name)
                        page_resp = client.messages.create(
                            model="claude-sonnet-4-5",
                            max_tokens=3000,
                            messages=[{"role": "user", "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
                                {"type": "text", "text": f"这是学生作文的第{i+1}页（共{len(all_image_bytes)}页）。请把这一页的手写文字逐字逐句准确转录成文字。保留分段结构，用换行表示分段。只输出转录的文字，不要加任何说明或页码标注。"}
                            ]}]
                        )
                        all_pages.append(page_resp.content[0].text.strip())
                    ocr_text = "\n".join(all_pages)

                st.session_state['ocr_text'] = ocr_text
                st.session_state['image_bytes'] = all_image_bytes[0]
                st.session_state['all_image_bytes'] = all_image_bytes
                st.session_state['all_image_names'] = [f.name for f in uploaded_files]
                st.session_state['selected_assignment'] = selected_assignment
                st.session_state['student_id'] = student_id
                st.session_state['student_name'] = student_name
                st.session_state['tts_lang'] = tts_lang
                st.session_state['ocr_done'] = True
                st.rerun()

            except Exception as e:
                st.error(f"识别出错：{e}")

# ═══════════════════════════════════════════════════════════
# STAGE 2 — OCR verification
# ═══════════════════════════════════════════════════════════
elif st.session_state['ocr_done'] and not st.session_state['feedback']:

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="step-badge">4</span> **核对识别文字**', unsafe_allow_html=True)
    st.markdown('<div class="ocr-warning">⚠️ 请仔细核对下面识别出来的文字，如有错误请直接修改，然后再点击"提交批改"。这也是你重新检查自己作文的好机会！</div>', unsafe_allow_html=True)

    col_orig, col_ocr = st.columns(2)
    with col_orig:
        all_imgs = st.session_state.get('all_image_bytes', [st.session_state['image_bytes']])
        st.markdown(f"**📸 原图（共{len(all_imgs)}页）**")
        for i, img_b in enumerate(all_imgs):
            st.image(img_b, caption=f"第{i+1}页", use_column_width=True)
    with col_ocr:
        st.markdown("**📝 识别出的文字（可直接修改）**")
        st.caption("如识别不准确，可借助其他工具识别后粘贴到这里，再点提交。")
        corrected_text = st.text_area(
            label="识别文字",
            value=st.session_state['ocr_text'],
            height=500,
            label_visibility="collapsed"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    col_back, col_submit = st.columns(2)
    with col_back:
        if st.button("← 重新上传"):
            st.session_state['ocr_done'] = False
            st.rerun()
    with col_submit:
        if st.button("🚀 确认无误，提交批改！"):
            with st.spinner("AI 正在仔细批改你的作文，请稍候约30秒……"):
                try:
                    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                    asgn = st.session_state['selected_assignment']
                    genre = asgn['genre']
                    rubric = asgn.get('rubric', '')
                    prompt_text = asgn['prompt']
                    requirements = asgn.get('requirements', '')
                    exam_level = asgn.get('exam_level', 'HCL')  # 默认 HCL，向后兼容旧数据

                    try:
                        focus_list = json.loads(asgn.get('focus_areas') or '[]')
                    except:
                        focus_list = []

                    # ── 用新的 SEAB 标准 prompt 引擎 ──────────────
                    system_prompt = build_grading_prompt(
                        exam_level=exam_level,
                        genre=genre,
                        prompt_text=prompt_text,
                        requirements=requirements,
                        focus_areas=focus_list,
                        custom_rubric=rubric if rubric else None,
                    )

                    user_msg = build_user_message(
                        prompt_text=prompt_text,
                        requirements=requirements,
                        genre=genre,
                        essay_text=corrected_text,
                    )

                    # ── API调用：批改+范文一次完成 ───────────
                    with st.spinner("AI 正在批改你的作文，请稍候约40秒……"):
                        response = client.messages.create(
                            model="claude-sonnet-4-5",
                            max_tokens=8000,
                            system=system_prompt,
                            messages=[{"role": "user", "content": user_msg}]
                        )
                    raw = response.content[0].text.strip()

                    # 清理markdown标记
                    if "```" in raw:
                        parts = raw.split("```")
                        for part in parts:
                            part = part.strip()
                            if part.startswith("json"):
                                part = part[4:].strip()
                            if part.startswith("{"):
                                raw = part
                                break

                    # 提取 { ... } 内容
                    if not raw.strip().startswith("{"):
                        start = raw.find("{")
                        end = raw.rfind("}") + 1
                        if start != -1 and end > start:
                            raw = raw[start:end]

                    raw = raw.strip()

                    # ── 核心修复：清理JSON字符串值里的非法双引号 ──
                    # AI有时在字符串值里写了双引号，如："analysis":"他写"很脏""
                    # 用状态机扫描，把字符串值内部的裸双引号替换成中文引号
                    import re as _json_re
                    def fix_json_quotes(s):
                        result = []
                        in_string = False
                        escape_next = False
                        i = 0
                        while i < len(s):
                            c = s[i]
                            if escape_next:
                                result.append(c)
                                escape_next = False
                            elif c == '\\':
                                result.append(c)
                                escape_next = True
                            elif c == '"':
                                if not in_string:
                                    in_string = True
                                    result.append(c)
                                else:
                                    # 检查是否是合法的字符串结束符
                                    # 合法：后面跟着 : , } ] 或空白
                                    j = i + 1
                                    while j < len(s) and s[j] in ' \t\n\r':
                                        j += 1
                                    next_char = s[j] if j < len(s) else ''
                                    if next_char in ':,}]':
                                        in_string = False
                                        result.append(c)
                                    else:
                                        # 非法双引号，替换成中文引号
                                        result.append('\u201c' if len(result) > 0 else '\u201d')
                            else:
                                result.append(c)
                            i += 1
                        return ''.join(result)

                    try:
                        feedback = json.loads(raw)
                    except json.JSONDecodeError:
                        # 尝试修复引号问题
                        fixed = fix_json_quotes(raw)
                        try:
                            feedback = json.loads(fixed)
                        except json.JSONDecodeError as parse_err:
                            st.error(f"JSON解析失败：{parse_err}")
                            st.text("AI原始返回（用于调试）：")
                            st.code(raw[:1500])
                            st.stop()

                    sub_id = save_submission(
                        asgn['id'],
                        st.session_state['student_id'],
                        st.session_state['student_name'],
                        st.session_state['image_bytes'],
                        corrected_text,
                        feedback
                    )
                    st.session_state['feedback'] = feedback
                    st.session_state['sub_id'] = sub_id
                    st.rerun()

                except json.JSONDecodeError:
                    st.error("AI返回格式有误，请重试。")
                    st.code(raw[:500])
                except Exception as e:
                    st.error(f"发生错误：{e}")

# ═══════════════════════════════════════════════════════════
# STAGE 3 — Show feedback (分层展示)
# ═══════════════════════════════════════════════════════════
elif st.session_state['feedback']:

    fb = st.session_state['feedback']
    sub_id = st.session_state.get('sub_id')
    lang = st.session_state.get('tts_lang', '普通话 (Mandarin)')
    name = st.session_state.get('student_name', '同学')

    if sub_id:
        mark_viewed(sub_id)

    scores = fb.get('scores', {})
    grade = fb.get('grade_estimate', '')
    strengths = fb.get('strengths', [])
    issues = fb.get('issues', {})
    lang_issues = issues.get('language', [])
    struct_issues = issues.get('structure', [])
    content_issues = issues.get('content', [])
    upgrades = fb.get('upgrade_table', [])
    overall = fb.get('overall_suggestion', '')
    encourage = fb.get('encouragement', '')
    audio_script = fb.get('audio_script', '')
    if not audio_script:
        audio_script = f"{name}同学，你好！{'。'.join(strengths)}。{overall}。{encourage}"

    total_issues = len(lang_issues) + len(struct_issues) + len(content_issues)

    # ── 顶部摘要卡片 ─────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a1a2e,#0f3460);border-radius:20px;
        padding:1.5rem 2rem;margin-bottom:1.5rem;color:white;">
        <div style="font-size:1.1rem;color:#f0c27f;font-family:'Noto Serif SC',serif;
            margin-bottom:1rem;">📋 {name} 的作文批改结果</div>
        <div style="display:flex;gap:1.5rem;flex-wrap:wrap;align-items:center;">
            <div style="text-align:center;">
                <div style="font-size:0.75rem;color:#b8c5d6;">预估等级</div>
                <div style="font-size:2.8rem;font-weight:700;color:#f0c27f;
                    font-family:'Noto Serif SC',serif;line-height:1.1;">{grade}</div>
            </div>
            <div style="flex:1;min-width:200px;">
                <div style="font-size:0.85rem;color:#b8c5d6;margin-bottom:0.4rem;">
                    发现 <strong style="color:#f0c27f">{total_issues}</strong> 个问题
                    · <strong style="color:#7ecb8f">{len(strengths)}</strong> 个优点
                </div>
                <div style="font-size:0.9rem;color:#e0e8f0;line-height:1.6;">{overall}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 雷达图 ───────────────────────────────────────────────
    if scores:
        try:
            import plotly.graph_objects as go
            dims = list(scores.keys())
            vals = list(scores.values())
            fig = go.Figure(go.Scatterpolar(
                r=vals + [vals[0]], theta=dims + [dims[0]],
                fill='toself',
                fillcolor='rgba(15,52,96,0.15)',
                line=dict(color='#0f3460', width=2.5),
                marker=dict(size=7, color='#f0c27f', line=dict(color='#0f3460', width=1.5))
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0,10], tickfont=dict(size=10))),
                showlegend=False, height=300,
                margin=dict(l=50,r=50,t=30,b=30),
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.caption(f"图表暂时无法显示：{e}")

    tts_voice = "zh-CN-XiaoxiaoNeural" if "普通话" in lang else "en-US-JennyNeural"

    # ══════════════════════════════════════════════════════════
    # 模块一：语音总评 + 优点
    # ══════════════════════════════════════════════════════════
    with st.expander("🔊 老师语音总评 + 优点", expanded=True):
        # 优点
        if strengths:
            st.markdown(f"""
            <div style="background:#e8f5e9;border-radius:10px;padding:0.8rem 1rem;
                margin-bottom:0.8rem;border-left:4px solid #43a047;">
                <div style="font-size:0.8rem;color:#2e7d32;font-weight:600;
                    margin-bottom:0.4rem;">✅ 优点</div>
                {"".join([f'<div style="color:#1b5e20;font-size:0.93rem;margin-bottom:0.3rem;">• {s}</div>' for s in strengths])}
            </div>""", unsafe_allow_html=True)
        # 总评文字
        st.markdown(f"""
        <div style="background:#fdf8ee;border-radius:8px;padding:0.8rem 1rem;
            font-size:0.9rem;color:#3a3020;font-style:italic;
            margin-bottom:0.8rem;border-left:3px solid #f0c27f;">
            💬 {audio_script}
        </div>""", unsafe_allow_html=True)
        # 语音播放
        try:
            import asyncio, edge_tts, io as _io
            async def _gen_audio(text, voice):
                com = edge_tts.Communicate(text, voice=voice, rate="-5%")
                buf = _io.BytesIO()
                async for chunk in com.stream():
                    if chunk["type"] == "audio": buf.write(chunk["data"])
                buf.seek(0); return buf
            _full_audio = audio_script + "。" + "。".join(strengths)
            st.audio(asyncio.run(_gen_audio(_full_audio, tts_voice)), format="audio/mp3")
        except Exception as e:
            st.caption(f"语音暂时不可用：{e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 模块二：改字词句 = 原文标注 + 对照表格
    # ══════════════════════════════════════════════════════════
    highlight_errors = fb.get('highlight_errors', [])
    ocr_text_display = st.session_state.get('ocr_text', '')
    # 分类：错别字 vs 病句/弱句
    typos = [e for e in highlight_errors if e.get('type') == '错别字']
    weak_sentences = [e for e in highlight_errors if e.get('type') != '错别字']
    # 对照表：只用 lang_issues（病句/弱句），不含错别字
    upgrades = fb.get('upgrade_table', [])

    total_lang = len(lang_issues) + len(upgrades)
    with st.expander(f"✏️ 改字词句  （{len(typos)} 个错别字，{len(lang_issues)+len(weak_sentences)} 处病句/弱句）", expanded=True):

        # ── 上半：原文标注（全部红色）──────────────────────────
        if highlight_errors and ocr_text_display:
            st.caption("🔴 红色高亮 = 需要修改的字词句（悬停看改法）")
            highlighted = ocr_text_display
            sorted_errors = sorted(highlight_errors,
                key=lambda x: len(x.get('text','')), reverse=True)
            for err in sorted_errors:
                err_text = err.get('text', '')
                improved = err.get('improved', '')
                if not err_text or err_text not in highlighted:
                    continue
                tooltip = f"→ {improved}" if improved else "需要修改"
                replacement = (
                    f'<mark style="background:#ffcdd2;color:#b71c1c;'
                    f'border-radius:3px;padding:0 2px;cursor:help;'
                    f'border-bottom:2px solid #ef9a9a;"'
                    f' title="{tooltip}">{err_text}</mark>'
                )
                highlighted = highlighted.replace(err_text, replacement, 1)
            highlighted_html = highlighted.replace('\n', '<br>')
            st.markdown(f"""
            <div style="background:white;border-radius:12px;padding:1.1rem 1.3rem;
                border:1px solid #e0e7ef;font-size:0.95rem;line-height:2.2;
                font-family:'Noto Serif SC',serif;color:#1a1a2e;
                box-shadow:0 2px 10px rgba(0,0,0,0.05);margin-bottom:1rem;">
                {highlighted_html}
            </div>""", unsafe_allow_html=True)

        # ── 下半：对照表格（只含病句/弱句，不含错别字）──────
        if lang_issues or upgrades:
            st.markdown("**📊 病句/弱句对照表**")

            # 表头 - 两栏：原句 + 优秀版
            st.markdown("""
            <div style="display:grid;grid-template-columns:1fr 1fr 48px;
                gap:4px;margin-bottom:4px;">
                <div style="background:#1a1a2e;color:#f0c27f;border-radius:6px;
                    padding:0.4rem 0.7rem;font-size:0.78rem;font-weight:600;">
                    ❌ 原句</div>
                <div style="background:#0f3460;color:#f0c27f;border-radius:6px;
                    padding:0.4rem 0.7rem;font-size:0.78rem;font-weight:600;">
                    ⭐ 优秀版</div>
                <div style="background:#1a1a2e;border-radius:6px;
                    padding:0.4rem 0.3rem;font-size:0.78rem;"></div>
            </div>""", unsafe_allow_html=True)

            # 合并 lang_issues 和 upgrades 按顺序显示
            shown = []
            all_items = []
            for item in lang_issues:
                orig = item.get('original','')
                imp = item.get('improved','')
                lv3 = ''
                for u in upgrades:
                    u_orig = u.get('original','')
                    if u_orig and (u_orig in orig or orig in u_orig):
                        lv3 = u.get('level3','')
                        shown.append(u_orig)
                        break
                all_items.append((orig, imp, lv3))

            # 剩余 upgrades（没有匹配 lang_issue 的）
            for u in upgrades:
                u_orig = u.get('original','')
                if not any(u_orig in lo or lo in u_orig for lo in [x[0] for x in all_items]):
                    all_items.append((u_orig, u.get('level2',''), u.get('level3','')))

            for i, (orig, imp, lv3) in enumerate(all_items):
                if not orig: continue
                best = lv3 if lv3 else imp
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 1fr 48px;
                    gap:4px;margin-bottom:4px;">
                    <div style="background:#fce4ec;border-radius:6px;
                        padding:0.5rem 0.7rem;font-size:0.88rem;color:#b71c1c;
                        text-decoration:line-through;">{orig}</div>
                    <div style="background:#e8eaf6;border-radius:6px;
                        padding:0.5rem 0.7rem;font-size:0.88rem;color:#1a237e;
                        font-weight:500;">{best}</div>
                    <div style="background:white;border-radius:6px;
                        padding:0.2rem;display:flex;align-items:center;
                        justify-content:center;">🔊</div>
                </div>""", unsafe_allow_html=True)
                try:
                    import asyncio, edge_tts, io as _io
                    async def _ta(t, v):
                        c = edge_tts.Communicate(t, voice=v, rate="-5%")
                        b = _io.BytesIO()
                        async for ch in c.stream():
                            if ch["type"] == "audio": b.write(ch["data"])
                        b.seek(0); return b
                    _ttxt = f"原句：{orig}。改成：{best}"
                    st.audio(asyncio.run(_ta(_ttxt, tts_voice)), format="audio/mp3")
                except: pass

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 模块三：写作要求专项批改
    # ══════════════════════════════════════════════════════════
    req_feedback = fb.get('requirements_feedback', [])
    _asgn = st.session_state.get('selected_assignment', {})
    _reqs_raw = _asgn.get('requirements', '') if _asgn else ''
    import re as _re2
    if _reqs_raw:
        _rt = _re2.sub(r'[（(]\d+[）)]', ';', _reqs_raw)
        _rt = _rt.replace('；',';').replace('\n',';')
        _req_list = [r.strip().lstrip('；;，,、') for r in _rt.split(';')
                     if r.strip() and len(r.strip()) > 3]
    else:
        _req_list = []

    if req_feedback:
        with st.expander(f"📝 写作要求专项批改  ({len(req_feedback)} 项)", expanded=True):
            for rf in req_feedback:
                req_num = rf.get('req_num', 0)
                achieved = rf.get('achieved', '')
                analysis = rf.get('analysis', '')
                example = rf.get('example', '')
                req_label = _req_list[req_num-1] if req_num > 0 and req_num <= len(_req_list) else f"要求{req_num}"
                if achieved == "做到了":
                    border="#43a047"; bg_h="#e8f5e9"; badge_bg="#43a047"; icon="✅"
                elif achieved == "部分做到":
                    border="#f9a825"; bg_h="#fff8e1"; badge_bg="#f9a825"; icon="🔶"
                else:
                    border="#e53935"; bg_h="#fce4ec"; badge_bg="#e53935"; icon="⚠️"
                tts_req = f"{req_label}：{achieved}。{analysis}。" + (f"修改例子：{example}" if example and achieved != "做到了" else "")
                st.markdown(f"""
                <div style="background:white;border-radius:12px;padding:0;
                    margin-bottom:1rem;border:1.5px solid {border};overflow:hidden;
                    box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                    <div style="background:{bg_h};padding:0.6rem 1rem;
                        display:flex;align-items:center;gap:0.5rem;">
                        <span style="background:{badge_bg};color:white;border-radius:6px;
                            padding:0.15rem 0.6rem;font-size:0.78rem;font-weight:600;">
                            {icon} 要求{req_num}</span>
                        <span style="font-size:0.88rem;font-weight:600;
                            color:#1a1a2e;flex:1;">{req_label}</span>
                        <span style="background:{badge_bg};color:white;border-radius:20px;
                            padding:0.1rem 0.6rem;font-size:0.75rem;">{achieved}</span>
                    </div>
                    <div style="padding:0.7rem 1rem;">
                        <div style="font-size:0.9rem;color:#333;margin-bottom:{'0.5rem' if example and achieved != '做到了' else '0'};">
                            {analysis}</div>
                        {"<div style='background:#1a1a2e;border-radius:8px;padding:0.6rem 0.9rem;'><div style='font-size:0.72rem;color:#f0c27f;margin-bottom:0.3rem;'>✏️ 修改例子</div><div style='color:#e8f0fe;font-size:0.9rem;line-height:1.7;'>" + example + "</div></div>" if example and achieved != "做到了" else ""}
                    </div>
                </div>""", unsafe_allow_html=True)
                try:
                    import asyncio, edge_tts, io as _io
                    async def _ra(t, v):
                        c = edge_tts.Communicate(t, voice=v, rate="-5%")
                        b = _io.BytesIO()
                        async for ch in c.stream():
                            if ch["type"] == "audio": b.write(ch["data"])
                        b.seek(0); return b
                    st.audio(asyncio.run(_ra(tts_req, tts_voice)), format="audio/mp3")
                except: pass

        st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 模块四：结构与内容（AI发现 + 老师焦点 整合）
    # ══════════════════════════════════════════════════════════
    focus_feedback = fb.get('focus_feedback', [])
    all_other = [('struct', i) for i in struct_issues] + [('content', i) for i in content_issues]
    # 只有老师勾选了焦点，或AI发现了结构/内容问题，才显示这个模块
    total_m4 = len(focus_feedback) + len(all_other)
    # 如果只有AI自动发现的问题（老师没有勾选焦点），不显示
    show_m4 = len(focus_feedback) > 0 or (len(all_other) > 0 and len(focus_feedback) > 0)

    if show_m4:
        with st.expander(f"🏗️ 结构与内容  ({total_m4} 项)", expanded=True):

            # 老师勾选的焦点（主线）
            if focus_feedback:
                st.caption("📌 老师重点关注的方面")
                for ff in focus_feedback:
                    focus_name = ff.get('focus','')
                    rating = ff.get('rating','')
                    comment = ff.get('comment','')
                    suggestion = ff.get('suggestion','')
                    if rating == "好":
                        border="#43a047"; bg_f="#e8f5e9"; badge="#43a047"; icon="✅"
                    elif rating == "一般":
                        border="#f9a825"; bg_f="#fff8e1"; badge="#f9a825"; icon="🔶"
                    else:
                        border="#e53935"; bg_f="#fce4ec"; badge="#e53935"; icon="⚠️"
                    tts_ff = f"{focus_name}：{rating}。{comment}。" + (f"建议：{suggestion}" if suggestion else "")
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:0.8rem 1rem;
                        margin-bottom:0.7rem;border:1px solid {border};
                        box-shadow:0 1px 6px rgba(0,0,0,0.05);">
                        <div style="display:flex;align-items:center;gap:0.5rem;
                            margin-bottom:0.4rem;">
                            <span style="background:{badge};color:white;border-radius:4px;
                                padding:0.1rem 0.5rem;font-size:0.75rem;font-weight:600;">
                                {icon} {focus_name}</span>
                            <span style="background:{badge};color:white;border-radius:20px;
                                padding:0.1rem 0.5rem;font-size:0.73rem;">{rating}</span>
                        </div>
                        <div style="font-size:0.9rem;color:#333;margin-bottom:{'0.4rem' if suggestion else '0'};">
                            {comment}</div>
                        {"<div style='font-size:0.85rem;color:#4a148c;background:#f3e5f5;border-radius:6px;padding:0.4rem 0.7rem;'>💡 " + suggestion + "</div>" if suggestion else ""}
                    </div>""", unsafe_allow_html=True)
                    try:
                        import asyncio, edge_tts, io as _io
                        async def _ffa(t, v):
                            c = edge_tts.Communicate(t, voice=v, rate="-5%")
                            b = _io.BytesIO()
                            async for ch in c.stream():
                                if ch["type"] == "audio": b.write(ch["data"])
                            b.seek(0); return b
                        st.audio(asyncio.run(_ffa(tts_ff, tts_voice)), format="audio/mp3")
                    except: pass

            # AI发现的结构/内容问题
            if all_other:
                if focus_feedback:
                    st.markdown("---")
                    st.caption("🤖 AI发现的其他结构与内容问题")
                for i, (kind, item) in enumerate(all_other):
                    loc = item.get('location','')
                    prob = item.get('problem','')
                    sug = item.get('suggestion','')
                    color = "#1e88e5" if kind == 'struct' else "#e53935"
                    bg = "#e3f2fd" if kind == 'struct' else "#fce4ec"
                    label = "结构" if kind == 'struct' else "内容"
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:0.8rem 1rem;
                        margin-bottom:0.7rem;border:1px solid #e0e7ef;
                        box-shadow:0 1px 6px rgba(0,0,0,0.05);">
                        <div style="display:flex;align-items:center;gap:0.4rem;
                            margin-bottom:0.4rem;">
                            <span style="background:{color};color:white;border-radius:4px;
                                padding:0.1rem 0.4rem;font-size:0.73rem;">{label}</span>
                            <span style="background:#1a1a2e;color:white;border-radius:4px;
                                padding:0.1rem 0.4rem;font-size:0.73rem;">{loc}</span>
                        </div>
                        <div style="background:{bg};border-radius:6px;padding:0.5rem 0.7rem;
                            font-size:0.9rem;color:#333;margin-bottom:0.4rem;">{prob}</div>
                        <div style="background:#f3e5f5;border-radius:6px;padding:0.5rem 0.7rem;
                            font-size:0.85rem;color:#4a148c;">💡 {sug}</div>
                    </div>""", unsafe_allow_html=True)
                    try:
                        import asyncio, edge_tts, io as _io
                        async def _oa(t, v):
                            c = edge_tts.Communicate(t, voice=v, rate="-5%")
                            b = _io.BytesIO()
                            async for ch in c.stream():
                                if ch["type"] == "audio": b.write(ch["data"])
                            b.seek(0); return b
                        st.audio(asyncio.run(_oa(f"{loc}。{prob}。建议：{sug}", tts_voice)), format="audio/mp3")
                    except: pass

        st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 鼓励
    # ══════════════════════════════════════════════════════════
    st.markdown(f"""
    <div style="background:#f3e5f5;border-radius:12px;padding:1rem 1.2rem;
        border-left:4px solid #8e24aa;margin-bottom:1rem;">
        <div style="font-size:0.8rem;color:#7b1fa2;margin-bottom:0.3rem;">✨ 鼓励</div>
        <div style="color:#4a148c;font-size:0.95rem;">{encourage}</div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 模块五：范文对照
    # ══════════════════════════════════════════════════════════
    model_paragraphs = fb.get('model_essay_paragraphs', [])
    if model_paragraphs:
        st.markdown("---")
        st.markdown("### 📄 范文对照：你的作文 vs 修改后版本")
        st.caption("左栏是你的原文，右栏是修改后的范文。**加粗蓝色**部分是改动的地方。")

        st.markdown("""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;
            background:#1a1a2e;border-radius:12px;overflow:hidden;margin-bottom:1rem;">
            <div style="background:#1a1a2e;padding:0.6rem 1rem;
                font-size:0.82rem;font-weight:600;color:#f0c27f;text-align:center;">
                📝 你的作文（原文）</div>
            <div style="background:#0f3460;padding:0.6rem 1rem;
                font-size:0.82rem;font-weight:600;color:#f0c27f;text-align:center;">
                ✨ 修改后范文</div>
        </div>""", unsafe_allow_html=True)

        for i, para in enumerate(model_paragraphs):
            orig_para = para.get('original', '')
            revised_para = para.get('revised', '')
            parts = revised_para.split('**')
            revised_html_parts = []
            for j, part in enumerate(parts):
                if j % 2 == 1:
                    revised_html_parts.append(
                        f'<strong style="color:#0d47a1;background:#e3f2fd;'
                        f'padding:0 3px;border-radius:3px;">{part}</strong>'
                    )
                else:
                    revised_html_parts.append(part.replace('\n', '<br>'))
            revised_html = ''.join(revised_html_parts)
            orig_html = orig_para.replace('\n', '<br>')
            bg_orig = "#fafafa" if i % 2 == 0 else "#f5f5f5"
            bg_rev = "#f0f7ff" if i % 2 == 0 else "#e8f4ff"
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;
                background:#ddd;margin-bottom:1px;">
                <div style="background:{bg_orig};padding:0.8rem 1rem;
                    font-size:0.92rem;line-height:1.9;color:#333;
                    border-left:3px solid #ccc;">
                    <span style="font-size:0.7rem;color:#999;display:block;
                        margin-bottom:0.2rem;">第 {i+1} 段</span>
                    {orig_html}
                </div>
                <div style="background:{bg_rev};padding:0.8rem 1rem;
                    font-size:0.92rem;line-height:1.9;color:#333;
                    border-left:3px solid #1e88e5;">
                    <span style="font-size:0.7rem;color:#1e88e5;display:block;
                        margin-bottom:0.2rem;">第 {i+1} 段（修改后）</span>
                    {revised_html}
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        full_revised = "\n".join([p.get('revised','').replace('**','') for p in model_paragraphs])
        st.markdown("""<div style="background:#0f3460;border-radius:10px;padding:0.6rem 1rem;
            margin-bottom:0.5rem;"><span style="color:#f0c27f;">🔊</span>
            <span style="color:#b8c5d6;font-size:0.85rem;margin-left:0.5rem;">
            朗读修改后范文</span></div>""", unsafe_allow_html=True)
        try:
            import asyncio, edge_tts, io as _io
            async def _model_audio(t, v):
                c = edge_tts.Communicate(t, voice=v, rate="-5%")
                b = _io.BytesIO()
                async for ch in c.stream():
                    if ch["type"] == "audio": b.write(ch["data"])
                b.seek(0); return b
            st.audio(asyncio.run(_model_audio(full_revised[:1500], tts_voice)), format="audio/mp3")
        except: pass

    if st.button("📝 提交另一篇作文"):
        for key in ['feedback','sub_id','ocr_done','ocr_text','image_bytes','all_image_bytes',
                    'all_image_names','selected_assignment','student_id','student_name','tts_lang']:
            st.session_state.pop(key, None)
        st.rerun()
