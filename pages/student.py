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

st.set_page_config(page_title="学生作文提交", page_icon="✏️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500&display=swap');
* { font-family: 'Noto Sans SC', sans-serif; }
h1,h2,h3 { font-family: 'Noto Serif SC', serif; }
.main { background: #faf8f5; }
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebarUserContent"] { display: none; }

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
                            max_tokens=16000,
                            system=system_prompt,
                            messages=[{"role": "user", "content": user_msg}]
                        )
                    raw = response.content[0].text.strip()

                    # 检测是否被 max_tokens 截断
                    stop_reason = getattr(response, 'stop_reason', None)
                    if stop_reason == 'max_tokens':
                        st.warning("⚠️ AI 输出过长被截断了，正在尝试修复…")

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
                            elif c == '\n' and in_string:
                                # 字符串内的裸换行符 → 转义成 \n
                                result.append('\\n')
                            elif c == '\r' and in_string:
                                result.append('\\n')
                            else:
                                result.append(c)
                            i += 1
                        return ''.join(result)

                    def try_recover_truncated_json(s):
                        """如果 JSON 被截断，尝试关闭未关闭的字符串/对象/数组"""
                        s = s.rstrip()
                        # 找到最后一个完整的字段（以 } 或 ] 结束的）
                        # 从尾部往回找，截到最后一个有效结构处
                        last_safe = -1
                        depth_brace = 0
                        depth_bracket = 0
                        in_str = False
                        esc = False
                        for i, c in enumerate(s):
                            if esc:
                                esc = False
                                continue
                            if c == '\\':
                                esc = True
                                continue
                            if c == '"':
                                in_str = not in_str
                                continue
                            if in_str:
                                continue
                            if c == '{': depth_brace += 1
                            elif c == '}':
                                depth_brace -= 1
                                if depth_brace == 0 and depth_bracket == 0:
                                    last_safe = i + 1
                            elif c == '[': depth_bracket += 1
                            elif c == ']':
                                depth_bracket -= 1
                                if depth_brace == 0 and depth_bracket == 0:
                                    last_safe = i + 1

                        # 如果找到了完整的顶层结构
                        if last_safe > 0:
                            return s[:last_safe]

                        # 否则尝试强制闭合
                        if in_str:
                            s = s + '"'
                        # 删掉最后一个不完整的字段（找最后一个逗号）
                        last_comma = s.rfind(',')
                        if last_comma > 0:
                            s = s[:last_comma]
                        # 补上缺失的括号
                        s = s + (']' * depth_bracket) + ('}' * depth_brace)
                        return s

                    feedback = None
                    try:
                        feedback = json.loads(raw)
                    except json.JSONDecodeError:
                        # 第一层：修复引号 + 换行符
                        fixed = fix_json_quotes(raw)
                        try:
                            feedback = json.loads(fixed)
                        except json.JSONDecodeError:
                            # 第二层：尝试恢复截断的 JSON
                            recovered = try_recover_truncated_json(fixed)
                            try:
                                feedback = json.loads(recovered)
                                st.info("✓ AI 输出被截断，已自动恢复部分内容")
                            except json.JSONDecodeError as parse_err:
                                st.error(f"❌ JSON解析失败：{parse_err}")
                                st.text(f"出错位置：第 {parse_err.lineno} 行，第 {parse_err.colno} 列")
                                st.text(f"AI 总输出长度：{len(raw)} 字符")
                                with st.expander("查看 AI 原始返回（用于调试）"):
                                    st.code(raw)
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

    # ── 取出新数据 ──────────────────────────────────────────
    scores = fb.get('scores', {})
    content_score = scores.get('content', 0)
    language_score = scores.get('language', 0)
    total_score = scores.get('total', content_score + language_score)

    rationale = fb.get('grading_rationale', {})
    content_level = rationale.get('content_level', '?')
    language_level = rationale.get('language_level', '?')
    content_reason = rationale.get('content_reason', '')
    language_reason = rationale.get('language_reason', '')

    grade = fb.get('grade_estimate', '')
    grade_distance = fb.get('grade_distance', '')
    audio_script = fb.get('audio_script', '')
    strengths = fb.get('strengths', [])
    overall = fb.get('overall_suggestion', '')
    encourage = fb.get('encouragement', '')
    coaching = fb.get('coaching_advice', [])
    paragraphs = fb.get('paragraph_feedback', [])
    model_basic = fb.get('model_essay_basic', '')
    model_advanced = fb.get('model_essay_advanced', '')

    if not audio_script:
        audio_script = f"{name}同学，{overall}。{encourage}"

    # ══════════════════════════════════════════════════════════
    # 模块 0:返回主页按钮
    # ══════════════════════════════════════════════════════════
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← 返回主页"):
            st.switch_page("app.py")

    # ══════════════════════════════════════════════════════════
    # 模块 1:精简评分卡 — 顶部展示分数 + 等级
    # ══════════════════════════════════════════════════════════
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a1a2e,#0f3460);border-radius:20px;
        padding:1.5rem 2rem;margin:1rem 0 1.5rem;color:white;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;">
            <div>
                <div style="font-size:1rem;color:#f0c27f;font-family:'Noto Serif SC',serif;
                    margin-bottom:0.3rem;">📋 {name} 的作文批改结果</div>
                <div style="font-size:0.85rem;color:#b8c5d6;">基于新加坡考评局（SEAB）官方评分标准</div>
            </div>
            <div style="text-align:center;background:rgba(240,194,127,0.15);padding:0.6rem 1.5rem;
                border-radius:12px;border:1px solid rgba(240,194,127,0.3);">
                <div style="font-size:0.7rem;color:#b8c5d6;margin-bottom:0.2rem;">预估等级</div>
                <div style="font-size:2.5rem;font-weight:700;color:#f0c27f;
                    font-family:'Noto Serif SC',serif;line-height:1;">{grade}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 三列分数展示
    # 根据考试段拿正确的满分值
    asgn_for_max = st.session_state.get('selected_assignment', {})
    exam_lvl_for_max = asgn_for_max.get('exam_level', 'HCL') if asgn_for_max else 'HCL'
    try:
        from prompts import EXAM_LEVELS as _EL
        _cfg = _EL.get(exam_lvl_for_max, _EL['HCL'])
        max_content = _cfg['content_max']
        max_language = _cfg['language_max']
        max_total = _cfg['essay_total']
    except:
        max_content, max_language, max_total = 30, 30, 60

    col_c, col_l, col_t = st.columns(3)
    with col_c:
        st.markdown(f"""
        <div style="background:white;border-radius:12px;padding:1rem;border:1px solid #e8e0d5;
            text-align:center;">
            <div style="font-size:0.8rem;color:#888;">内容</div>
            <div style="font-size:2rem;font-weight:700;color:#1a1a2e;font-family:'Noto Serif SC',serif;">
                {content_score}<span style="font-size:1rem;color:#888;">/{max_content}</span>
            </div>
            <div style="font-size:0.8rem;color:#0f3460;font-weight:500;">{content_level}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_l:
        st.markdown(f"""
        <div style="background:white;border-radius:12px;padding:1rem;border:1px solid #e8e0d5;
            text-align:center;">
            <div style="font-size:0.8rem;color:#888;">语文</div>
            <div style="font-size:2rem;font-weight:700;color:#1a1a2e;font-family:'Noto Serif SC',serif;">
                {language_score}<span style="font-size:1rem;color:#888;">/{max_language}</span>
            </div>
            <div style="font-size:0.8rem;color:#0f3460;font-weight:500;">{language_level}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_t:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#fdf8ee,#f5e9d3);border-radius:12px;padding:1rem;
            border:1px solid #f0c27f;text-align:center;">
            <div style="font-size:0.8rem;color:#7a5c1e;">总分</div>
            <div style="font-size:2rem;font-weight:700;color:#7a5c1e;font-family:'Noto Serif SC',serif;">
                {total_score}<span style="font-size:1rem;color:#7a5c1e;">/{max_total}</span>
            </div>
            <div style="font-size:0.8rem;color:#7a5c1e;font-weight:500;">{grade_distance[:30] if grade_distance else ''}</div>
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 模块 2:总评 + 优点 + 教练建议(语音 + 文字)
    # ══════════════════════════════════════════════════════════
    tts_voice = "zh-CN-XiaoxiaoNeural" if "普通话" in lang else "en-US-JennyNeural"

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔊 老师总评 + 进步建议", expanded=True):
        # 语音播放
        try:
            import asyncio, edge_tts, io as _io
            async def _gen_audio(text, voice):
                com = edge_tts.Communicate(text, voice=voice, rate="-5%")
                buf = _io.BytesIO()
                async for chunk in com.stream():
                    if chunk["type"] == "audio": buf.write(chunk["data"])
                buf.seek(0); return buf
            _full_audio = audio_script
            st.audio(asyncio.run(_gen_audio(_full_audio, tts_voice)), format="audio/mp3")
        except Exception as e:
            st.caption(f"语音暂时不可用:{e}")

        # 文字总评
        st.markdown(f"""
        <div style="background:#fdf8ee;border-radius:8px;padding:0.9rem 1rem;
            font-size:0.95rem;color:#3a3020;margin:0.8rem 0;border-left:3px solid #f0c27f;">
            💬 {audio_script}
        </div>""", unsafe_allow_html=True)

        # 优点 - 1-2 句简洁带过
        if strengths:
            strengths_text = " · ".join(strengths)
            st.markdown(f"""
            <div style="background:#e8f5e9;border-radius:8px;padding:0.7rem 1rem;
                margin:0.5rem 0;border-left:3px solid #43a047;">
                <span style="color:#2e7d32;font-weight:600;font-size:0.85rem;">✅ 优点：</span>
                <span style="color:#1b5e20;font-size:0.9rem;">{strengths_text}</span>
            </div>""", unsafe_allow_html=True)

        # 整体建议
        if overall:
            st.markdown(f"""
            <div style="background:#fff3e0;border-radius:8px;padding:0.7rem 1rem;
                margin:0.5rem 0;border-left:3px solid #fb8c00;">
                <span style="color:#e65100;font-weight:600;font-size:0.85rem;">🎯 最重要的建议：</span>
                <span style="color:#5d3700;font-size:0.9rem;">{overall}</span>
            </div>""", unsafe_allow_html=True)

        # 教练式建议
        if coaching:
            coaching_html = "".join([
                f'<div style="color:#1a3a5c;font-size:0.9rem;margin:0.3rem 0;padding-left:1rem;">→ {c}</div>'
                for c in coaching
            ])
            st.markdown(f"""
            <div style="background:#e3f2fd;border-radius:8px;padding:0.8rem 1rem;
                margin:0.5rem 0;border-left:3px solid #1e88e5;">
                <div style="color:#0d47a1;font-weight:600;font-size:0.9rem;margin-bottom:0.4rem;">
                    📝 老师的教练建议
                </div>
                {coaching_html}
            </div>""", unsafe_allow_html=True)

        # 鼓励语
        if encourage:
            st.markdown(f"""
            <div style="background:#f3e5f5;border-radius:8px;padding:0.7rem 1rem;
                margin:0.5rem 0;border-left:3px solid #8e24aa;">
                <span style="color:#6a1b9a;font-weight:600;font-size:0.85rem;">💖 </span>
                <span style="color:#4a148c;font-size:0.9rem;font-style:italic;">{encourage}</span>
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 模块 3:评分依据(可折叠,默认折叠 — 让学生看主要的)
    # ══════════════════════════════════════════════════════════
    with st.expander("📊 评分依据（按 SEAB 官方等级标准）", expanded=False):
        st.markdown(f"""
        <div style="background:white;border-radius:8px;padding:0.9rem 1rem;margin:0.4rem 0;
            border:1px solid #e8e0d5;">
            <div style="color:#0f3460;font-weight:600;font-size:0.9rem;margin-bottom:0.3rem;">
                内容 {content_score}分 — {content_level}
            </div>
            <div style="color:#555;font-size:0.85rem;line-height:1.6;">{content_reason}</div>
        </div>
        <div style="background:white;border-radius:8px;padding:0.9rem 1rem;margin:0.4rem 0;
            border:1px solid #e8e0d5;">
            <div style="color:#0f3460;font-weight:600;font-size:0.9rem;margin-bottom:0.3rem;">
                语文 {language_score}分 — {language_level}
            </div>
            <div style="color:#555;font-size:0.85rem;line-height:1.6;">{language_reason}</div>
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 模块 4:段落式批改(v3 核心 — 阶段 A:简化版,阶段 B 升级为左右对照)
    # ══════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📖 逐段批改与修改示范")

    if not paragraphs:
        st.info("AI 没有返回段落级批改。请检查作文内容。")
    else:
        # 基础版 / 进阶版切换
        st.markdown('<div style="margin:0.8rem 0;color:#555;font-size:0.9rem;">'
                    '请选择修改示范的难度：</div>', unsafe_allow_html=True)
        version = st.radio(
            "修改难度",
            ["📘 基础版（小六水平 · 文通字顺）", "🌟 进阶版（A1+水平 · 用词丰富）"],
            horizontal=True, label_visibility="collapsed",
            key="version_select"
        )
        is_basic = "基础版" in version

        st.markdown("<br>", unsafe_allow_html=True)

        for p in paragraphs:
            para_num = p.get('para_num', '?')
            para_role = p.get('para_role', '')
            original = p.get('original_text', '')
            lang_iss = p.get('language_issues', [])
            struct_iss = p.get('structure_content_issues', [])
            highlights = p.get('highlights', '')
            revised = p.get('revised_basic' if is_basic else 'revised_advanced', '')

            # 段落标题
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:10px 10px 0 0;
                padding:0.7rem 1rem;color:#f0c27f;font-family:'Noto Serif SC',serif;
                font-size:1rem;font-weight:600;margin-top:1.2rem;">
                第 {para_num} 段 · {para_role}
            </div>
            """, unsafe_allow_html=True)

            # 学生原文
            st.markdown(f"""
            <div style="background:#fafaf0;border:1px solid #e8e0d5;border-top:none;
                padding:1rem 1.2rem;font-size:0.95rem;line-height:1.9;color:#2c2c2a;">
                <div style="font-size:0.75rem;color:#888;margin-bottom:0.4rem;font-weight:600;">
                    📝 你的原文
                </div>
                {original}
            </div>
            """, unsafe_allow_html=True)

            # 亮点(如有)
            if highlights:
                st.markdown(f"""
                <div style="background:#e8f5e9;border-left:4px solid #43a047;
                    padding:0.6rem 1rem;margin-top:0.4rem;border-radius:4px;">
                    <span style="color:#2e7d32;font-size:0.85rem;font-weight:600;">✨ 这段亮点：</span>
                    <span style="color:#1b5e20;font-size:0.88rem;">{highlights}</span>
                </div>
                """, unsafe_allow_html=True)

            # 语言问题(红色框)
            if lang_iss:
                lang_html = ""
                for li in lang_iss:
                    li_type = li.get('type', '问题')
                    li_orig = li.get('original', '')
                    li_imp = li.get('improved', '')
                    li_exp = li.get('explanation', '')
                    lang_html += f"""
                    <div style="background:white;border-radius:6px;padding:0.6rem 0.8rem;
                        margin:0.4rem 0;font-size:0.88rem;">
                        <span style="background:#c62828;color:white;border-radius:4px;
                            padding:0.1rem 0.5rem;font-size:0.75rem;margin-right:0.5rem;">{li_type}</span>
                        <span style="color:#c62828;text-decoration:line-through;">{li_orig}</span>
                        <span style="color:#888;margin:0 0.3rem;">→</span>
                        <span style="color:#2e7d32;font-weight:500;">{li_imp}</span>
                        <div style="color:#666;font-size:0.78rem;margin-top:0.2rem;
                            margin-left:0.5rem;">💡 {li_exp}</div>
                    </div>
                    """
                st.markdown(f"""
                <div style="background:#ffebee;border-left:4px solid #c62828;
                    padding:0.7rem 1rem;margin-top:0.4rem;border-radius:4px;">
                    <div style="color:#c62828;font-weight:600;font-size:0.85rem;margin-bottom:0.4rem;">
                        🔴 语言问题（错字 / 病句 / 弱句）
                    </div>
                    {lang_html}
                </div>
                """, unsafe_allow_html=True)

            # 结构内容问题(蓝色框)
            if struct_iss:
                struct_html = ""
                for si in struct_iss:
                    si_aspect = si.get('aspect', '')
                    si_problem = si.get('problem', '')
                    si_sugg = si.get('suggestion', '')
                    struct_html += f"""
                    <div style="background:white;border-radius:6px;padding:0.6rem 0.8rem;
                        margin:0.4rem 0;font-size:0.88rem;">
                        <div style="color:#1565c0;font-weight:600;margin-bottom:0.3rem;">
                            📐 {si_aspect}
                        </div>
                        <div style="color:#5d3700;margin-bottom:0.3rem;">问题：{si_problem}</div>
                        <div style="color:#1b5e20;">💡 建议：{si_sugg}</div>
                    </div>
                    """
                st.markdown(f"""
                <div style="background:#e3f2fd;border-left:4px solid #1565c0;
                    padding:0.7rem 1rem;margin-top:0.4rem;border-radius:4px;">
                    <div style="color:#0d47a1;font-weight:600;font-size:0.85rem;margin-bottom:0.4rem;">
                        🔵 结构与内容批改
                    </div>
                    {struct_html}
                </div>
                """, unsafe_allow_html=True)

            # 修改示范(根据用户选择显示基础版或进阶版)
            version_label = "📘 基础版修改" if is_basic else "🌟 进阶版修改"
            version_color = "#558b2f" if is_basic else "#6a1b9a"
            version_bg = "#f1f8e9" if is_basic else "#f3e5f5"
            st.markdown(f"""
            <div style="background:{version_bg};border-left:4px solid {version_color};
                padding:1rem 1.2rem;margin-top:0.5rem;border-radius:4px;">
                <div style="color:{version_color};font-weight:600;font-size:0.9rem;
                    margin-bottom:0.5rem;">{version_label}</div>
                <div style="color:#2c2c2a;font-size:0.95rem;line-height:1.9;">
                    {revised}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 模块 5:整篇范文(基础版 / 进阶版,按用户选择)
    # ══════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    if paragraphs:  # 只有当 paragraph_feedback 存在时才显示范文
        with st.expander(f"📖 整篇范文（{('基础版' if is_basic else '进阶版')}）", expanded=False):
            full_model = model_basic if is_basic else model_advanced
            if full_model:
                model_color = "#558b2f" if is_basic else "#6a1b9a"
                model_bg = "#f1f8e9" if is_basic else "#f3e5f5"
                st.markdown(f"""
                <div style="background:{model_bg};border-left:4px solid {model_color};
                    padding:1.2rem 1.5rem;border-radius:8px;font-size:0.95rem;line-height:1.95;
                    color:#2c2c2a;white-space:pre-wrap;">
                    {full_model}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("范文未生成,请重新提交。")

    # ══════════════════════════════════════════════════════════
    # 模块 6:再提交按钮
    # ══════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📝 提交另一篇作文"):
        for key in ['feedback','sub_id','ocr_done','ocr_text','image_bytes','all_image_bytes',
                    'all_image_names','selected_assignment','student_id','student_name','tts_lang']:
            st.session_state.pop(key, None)
        st.rerun()
