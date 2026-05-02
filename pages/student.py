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

# ── 顶部导航栏 ───────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1a1a2e,#0f3460);border-radius:12px;
    padding:0.9rem 1.5rem;margin-bottom:1rem;display:flex;justify-content:space-between;
    align-items:center;flex-wrap:wrap;gap:1rem;box-shadow:0 4px 16px rgba(0,0,0,0.08);">
    <div>
        <span style="color:#f0c27f;font-family:'Noto Serif SC',serif;font-size:1.15rem;font-weight:700;">
            📝 华文作文批改平台
        </span>
        <span style="color:#b8c5d6;font-size:0.8rem;margin-left:0.5rem;">
            学生作文提交
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 横向导航按钮 ──
st.markdown("""<style>
.nav-row .stButton > button {
    background: transparent; color: #1a1a2e; border: 1px solid #e8e0d5;
    border-radius: 8px; padding: 0.4rem 1rem; font-size: 0.9rem;
    font-weight: 500; width: 100%; height: 40px; transition: all 0.2s;
}
.nav-row .stButton > button:hover {
    background: #fdf8ee; border-color: #f0c27f; color: #7a5c1e;
    transform: none; box-shadow: none;
}
</style><div class="nav-row">""", unsafe_allow_html=True)
nav1, nav2, nav3, nav4 = st.columns(4)
with nav1:
    if st.button("🏠 首页", key="nav_home_s"):
        st.switch_page("app.py")
with nav2:
    st.button("🎓 学生作文提交", key="nav_student_s", disabled=True)
with nav3:
    if st.button("👩‍🏫 教师管理后台", key="nav_admin_s"):
        st.switch_page("pages/admin.py")
with nav4:
    if st.button("📈 学生进步追踪", key="nav_progress_s"):
        st.switch_page("pages/progress.py")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

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

                    # ── API调用：用 streaming 模式避免长输出超时 ───────────
                    with st.spinner("AI 正在批改你的作文，请稍候约40秒……"):
                        # max_tokens 16000 够用(已删除 model_essay 字段节省了 ~4000 tokens)
                        # 用 streaming 模式提高稳定性,避免长输出错误
                        full_text_chunks = []
                        stop_reason = None
                        with client.messages.stream(
                            model="claude-sonnet-4-5",
                            max_tokens=16000,
                            system=system_prompt,
                            messages=[{"role": "user", "content": user_msg}]
                        ) as stream:
                            for text_chunk in stream.text_stream:
                                full_text_chunks.append(text_chunk)
                            # 拿最终 message 看 stop_reason
                            final_message = stream.get_final_message()
                            stop_reason = final_message.stop_reason
                    raw = ''.join(full_text_chunks).strip()

                    # 检测是否被 max_tokens 截断
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

                    def aggressive_json_clean(s):
                        """更激进的清洗:处理常见 AI 输出错误"""
                        import re as _re
                        # 1. 把字符串内的中文双引号换成中文方括号
                        # 2. 把字符串内的英文单引号统一保留
                        # 3. 把 JSON 结构外的 markdown 代码块去掉
                        s = s.strip()
                        if s.startswith('```'):
                            # 移除 markdown 代码块标记
                            s = _re.sub(r'^```(?:json)?\s*', '', s)
                            s = _re.sub(r'\s*```$', '', s)
                        # 找到第一个 { 和最后一个 }
                        first_brace = s.find('{')
                        last_brace = s.rfind('}')
                        if first_brace >= 0 and last_brace > first_brace:
                            s = s[first_brace:last_brace + 1]
                        return s

                    def extract_partial_feedback(raw_text):
                        """终极兜底:从损坏的 JSON 里手动用正则提取关键字段"""
                        import re as _re
                        result = {}
                        # 提取 scores
                        sc_match = _re.search(r'"scores"\s*:\s*\{([^}]+)\}', raw_text)
                        if sc_match:
                            sc_str = sc_match.group(1)
                            try:
                                content = int(_re.search(r'"content"\s*:\s*(\d+)', sc_str).group(1))
                                language = int(_re.search(r'"language"\s*:\s*(\d+)', sc_str).group(1))
                                total_m = _re.search(r'"total"\s*:\s*(\d+)', sc_str)
                                total = int(total_m.group(1)) if total_m else content + language
                                result['scores'] = {'content': content, 'language': language, 'total': total}
                            except (AttributeError, ValueError):
                                pass
                        # 提取 grade_estimate
                        gm = _re.search(r'"grade_estimate"\s*:\s*"([^"]+)"', raw_text)
                        if gm: result['grade_estimate'] = gm.group(1)
                        # 提取 grade_distance
                        gd = _re.search(r'"grade_distance"\s*:\s*"([^"]+)"', raw_text)
                        if gd: result['grade_distance'] = gd.group(1)
                        # 提取 audio_script
                        au = _re.search(r'"audio_script"\s*:\s*"([^"]+)"', raw_text)
                        if au: result['audio_script'] = au.group(1)
                        # 提取 overall_suggestion
                        ov = _re.search(r'"overall_suggestion"\s*:\s*"([^"]+)"', raw_text)
                        if ov: result['overall_suggestion'] = ov.group(1)
                        # 提取 encouragement
                        en = _re.search(r'"encouragement"\s*:\s*"([^"]+)"', raw_text)
                        if en: result['encouragement'] = en.group(1)
                        # 默认空段落
                        result.setdefault('paragraph_feedback', [])
                        result.setdefault('coaching_advice', [])
                        result.setdefault('strengths', [])
                        return result

                    feedback = None
                    try:
                        feedback = json.loads(raw)
                    except json.JSONDecodeError:
                        # 第 1 层:激进清洗(去 markdown 代码块、修剪到大括号范围)
                        cleaned = aggressive_json_clean(raw)
                        try:
                            feedback = json.loads(cleaned)
                        except json.JSONDecodeError:
                            # 第 2 层:修复引号 + 换行符
                            fixed = fix_json_quotes(cleaned)
                            try:
                                feedback = json.loads(fixed)
                            except json.JSONDecodeError:
                                # 第 3 层:尝试恢复截断的 JSON
                                recovered = try_recover_truncated_json(fixed)
                                try:
                                    feedback = json.loads(recovered)
                                    st.info("✓ AI 输出被截断,已自动恢复部分内容")
                                except json.JSONDecodeError:
                                    # 第 4 层:终极兜底 — 用正则提取关键字段
                                    feedback = extract_partial_feedback(raw)
                                    if feedback.get('scores'):
                                        st.warning(
                                            "⚠️ AI 输出格式异常,已提取出分数和总评。"
                                            "段落级批改可能不完整,请重新提交一次以获得完整批改。"
                                        )
                                    else:
                                        st.error(
                                            "❌ AI 输出严重异常,无法提取批改结果。"
                                            "请稍后重新提交,或联系管理员。"
                                        )
                                        with st.expander("查看 AI 原始返回(用于调试)"):
                                            st.code(raw[:5000])
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
    # 整篇范文从段落 revised 自动拼起来(不依赖单独字段,节省 AI 输出 token)
    if paragraphs:
        model_basic = "\n\n".join([p.get('revised_basic', '') for p in paragraphs if p.get('revised_basic')])
        model_advanced = "\n\n".join([p.get('revised_advanced', '') for p in paragraphs if p.get('revised_advanced')])
    else:
        model_basic = fb.get('model_essay_basic', '')  # 兼容老数据
        model_advanced = fb.get('model_essay_advanced', '')

    if not audio_script:
        audio_script = f"{name}同学，{overall}。{encourage}"

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
        # 语音播放 - 读完整总评(包括优点、建议、教练建议)
        try:
            import asyncio, edge_tts, io as _io
            async def _gen_audio(text, voice):
                com = edge_tts.Communicate(text, voice=voice, rate="-5%")
                buf = _io.BytesIO()
                async for chunk in com.stream():
                    if chunk["type"] == "audio": buf.write(chunk["data"])
                buf.seek(0); return buf

            # 拼接完整语音内容
            _audio_parts = [audio_script] if audio_script else []
            if strengths:
                _audio_parts.append("你的优点是：" + "；".join(strengths))
            if overall:
                _audio_parts.append("最重要的建议：" + overall)
            if coaching:
                _audio_parts.append("老师的教练建议是。" + "。".join(coaching))
            if encourage:
                _audio_parts.append(encourage)
            _full_audio = "。".join([p.strip().rstrip("。") for p in _audio_parts if p]) + "。"

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
        # 默认基础版用于范文部分（每段独立切换在下面单独实现）
        is_basic = True

        # ── HTML 工具函数:在原文里嵌入红绿高亮 ────────────
        def html_escape(s):
            """HTML 转义"""
            return (str(s).replace('&', '&amp;').replace('<', '&lt;')
                    .replace('>', '&gt;').replace('"', '&quot;'))

        def build_highlighted_paragraph(orig_text, red_list, green_list):
            """
            把 original_text 转成带高亮的 HTML。
            红色 = 错字病句（用 <span class="red-hl"> 包裹,鼠标悬停看正确答案）
            绿色 = 弱句逻辑（用 <span class="green-hl"> 包裹,点击展开看分析,在右侧）
            """
            # 收集所有需要高亮的"片段 → HTML"映射
            replacements = []  # (start, end, replacement_html)

            for r in red_list:
                target = r.get('original', '')
                if not target or target not in orig_text:
                    continue
                improved = html_escape(r.get('improved', ''))
                explain = html_escape(r.get('explanation', ''))
                tooltip = f"{improved}　{explain}".strip().rstrip('　')
                hl_html = (f'<span class="red-hl" data-tooltip="{tooltip}">'
                           f'{html_escape(target)}'
                           f'<span class="tooltip-content">'
                           f'<b>正确写法：</b>{improved}<br>'
                           f'<span style="font-size:0.75rem;color:#aaa;">💡 {explain}</span>'
                           f'</span></span>')
                # 找所有匹配位置
                start = 0
                while True:
                    idx = orig_text.find(target, start)
                    if idx == -1:
                        break
                    replacements.append((idx, idx + len(target), hl_html))
                    start = idx + len(target)

            for idx_g, g in enumerate(green_list):
                target = g.get('original', '')
                if not target or target not in orig_text:
                    continue
                hl_html = (f'<span class="green-hl" data-green-idx="{idx_g+1}">'
                           f'{html_escape(target)}'
                           f'<sup class="green-num">{idx_g+1}</sup>'
                           f'</span>')
                start = 0
                while True:
                    idx = orig_text.find(target, start)
                    if idx == -1:
                        break
                    replacements.append((idx, idx + len(target), hl_html))
                    start = idx + len(target)

            # 按 start 位置排序,避免重叠 — 后插入不能覆盖前一个
            replacements.sort(key=lambda x: x[0])
            # 去重:如果两段重叠,优先红色（先 append 的）
            non_overlap = []
            last_end = -1
            for s, e, html in replacements:
                if s >= last_end:
                    non_overlap.append((s, e, html))
                    last_end = e

            # 从后往前替换以保持索引有效
            result_chunks = []
            cursor = 0
            for s, e, html in non_overlap:
                if s > cursor:
                    result_chunks.append(html_escape(orig_text[cursor:s]))
                result_chunks.append(html)
                cursor = e
            if cursor < len(orig_text):
                result_chunks.append(html_escape(orig_text[cursor:]))

            return ''.join(result_chunks)

        # ── 全局 CSS:高亮样式 + 鼠标悬停 tooltip ─────────────
        st.markdown('''
        <style>
        .red-hl {
            background: #ffebee;
            color: #c62828;
            padding: 0.05rem 0.2rem;
            border-radius: 3px;
            border-bottom: 2px solid #c62828;
            cursor: help;
            position: relative;
            display: inline-block;
        }
        .red-hl:hover { background: #ffcdd2; }
        .red-hl .tooltip-content {
            visibility: hidden;
            opacity: 0;
            position: absolute;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a2e;
            color: white;
            padding: 0.6rem 0.8rem;
            border-radius: 6px;
            font-size: 0.85rem;
            white-space: normal;
            min-width: 180px;
            max-width: 280px;
            text-align: left;
            line-height: 1.6;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: opacity 0.2s;
            pointer-events: none;
        }
        .red-hl:hover .tooltip-content {
            visibility: visible;
            opacity: 1;
        }
        .green-hl {
            background: #e8f5e9;
            color: #2e7d32;
            padding: 0.05rem 0.2rem;
            border-radius: 3px;
            border-bottom: 2px solid #43a047;
            cursor: pointer;
            display: inline-block;
        }
        .green-hl:hover { background: #c8e6c9; }
        .green-num {
            background: #43a047;
            color: white;
            font-size: 0.65rem;
            padding: 0 0.3rem;
            border-radius: 50%;
            margin-left: 0.15rem;
            font-weight: bold;
            vertical-align: super;
        }
        .para-card {
            background: linear-gradient(135deg,#1a1a2e,#16213e);
            border-radius: 10px 10px 0 0;
            padding: 0.7rem 1rem;
            color: #f0c27f;
            font-family: 'Noto Serif SC', serif;
            font-size: 1rem;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: -0.5rem;
        }
        .left-orig {
            background: #fafaf0;
            border: 1px solid #e8e0d5;
            border-top: none;
            padding: 1rem 1.2rem;
            font-size: 0.95rem;
            line-height: 2.1;
            color: #2c2c2a;
            border-radius: 0;
            min-height: 250px;
            height: 100%;
        }
        .right-fb {
            background: #fbfbfb;
            border: 1px solid #e8e0d5;
            border-top: none;
            padding: 1rem 1.2rem;
            font-size: 0.92rem;
            color: #2c2c2a;
            min-height: 250px;
            height: 100%;
        }
        .legend-tag {
            display: inline-block;
            font-size: 0.72rem;
            padding: 0.1rem 0.5rem;
            border-radius: 3px;
            margin-right: 0.4rem;
            font-weight: 500;
        }
        </style>
        ''', unsafe_allow_html=True)

        # ── 全局图例提示 ──
        st.markdown(
            '<div style="background:#fdf8ee;border-left:3px solid #f0c27f;'
            'padding:0.5rem 1rem;border-radius:6px;margin-bottom:1rem;font-size:0.83rem;color:#5d3700;">'
            '<span class="legend-tag" style="background:#ffebee;color:#c62828;border:1px solid #c62828;">Red</span>'
            '错字 / 病句（悬停看正确写法）　　'
            '<span class="legend-tag" style="background:#e8f5e9;color:#2e7d32;border:1px solid #43a047;">Green</span>'
            '弱句 / 逻辑 / 衔接（编号对应右侧）'
            '</div>',
            unsafe_allow_html=True
        )

        # ── 逐段渲染:左原文 / 右批改 ────────────
        for p in paragraphs:
            para_num = p.get('para_num', '?')
            para_role = p.get('para_role', '')
            original = p.get('original_text', '')
            # 兼容老数据:有些可能还是 language_issues
            red_list = p.get('red_issues', []) or []
            green_list = p.get('green_issues', []) or []
            if not red_list and not green_list and 'language_issues' in p:
                # 老结构:把所有 language_issues 当成红色
                old_iss = p.get('language_issues', [])
                for it in old_iss:
                    t = it.get('type', '')
                    if any(k in t for k in ['弱句', '逻辑', '衔接']):
                        green_list.append({
                            'type': t, 'original': it.get('original', ''),
                            'issue_detail': it.get('explanation', ''),
                            'suggestion': it.get('improved', '')
                        })
                    else:
                        red_list.append(it)

            struct_iss = p.get('structure_content_issues', [])
            highlights = p.get('highlights', '')
            revised_b = p.get('revised_basic', '')
            revised_a = p.get('revised_advanced', '')

            # 段落标题(横跨整行)
            st.markdown(
                f'<div class="para-card">第 {para_num} 段 · {para_role}</div>',
                unsafe_allow_html=True
            )

            # ── 整个段落用一个带边框的容器包起来 = 视觉单元 ──
            with st.container(border=True):
                # 左右两列 — 1:2 比例,左原文 / 右全部批改
                col_left, col_right = st.columns([1, 2], gap="small")

                with col_left:
                    highlighted = build_highlighted_paragraph(original, red_list, green_list)
                    st.markdown(
                        f'<div class="left-orig">'
                        f'<div style="font-size:0.75rem;color:#888;margin-bottom:0.6rem;font-weight:600;">'
                        f'📝 你的原文</div>'
                        f'<div>{highlighted}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                with col_right:
                    # ─────── 右栏纯 HTML 部分(亮点 + 不足 + 绿色弱句) ───────
                    right_parts = ['<div class="right-fb">']

                    # 1. Strengths(紧凑一行)
                    if highlights:
                        right_parts.append(
                            '<div style="background:#e8f5e9;border-left:3px solid #43a047;'
                            'padding:0.35rem 0.7rem;margin-bottom:0.4rem;border-radius:4px;'
                            'font-size:0.83rem;line-height:1.5;">'
                            f'<b style="color:#2e7d32;">Strengths：</b>'
                            f'<span style="color:#1b5e20;">{html_escape(highlights)}</span>'
                            '</div>'
                        )

                    # 2. 不足:错字病句简短一行(详情看左边悬停)
                    if red_list:
                        right_parts.append(
                            '<div style="background:#ffebee;border-left:3px solid #c62828;'
                            'padding:0.35rem 0.7rem;margin-bottom:0.4rem;border-radius:4px;'
                            'font-size:0.83rem;line-height:1.5;">'
                            f'<b style="color:#c62828;">不足：</b>'
                            f'<span style="color:#5d3700;">{len(red_list)} 处错字 / 病句</span>'
                            '<span style="color:#888;font-size:0.75rem;margin-left:0.4rem;">'
                            '（鼠标悬停左边红色字看正确写法）</span>'
                            '</div>'
                        )

                    # 3. 绿色弱句解释 — 编号对应原文
                    if green_list:
                        for i, g in enumerate(green_list):
                            g_orig = html_escape(g.get('original', ''))
                            g_detail = html_escape(g.get('issue_detail', ''))
                            g_sugg = html_escape(g.get('suggestion', ''))
                            right_parts.append(
                                '<div style="background:#f1f8e9;border-radius:5px;'
                                'padding:0.45rem 0.7rem;margin:0.3rem 0;font-size:0.83rem;'
                                'border-left:3px solid #43a047;line-height:1.55;">'
                                f'<div style="color:#2e7d32;font-weight:600;margin-bottom:0.15rem;font-size:0.78rem;">'
                                f'<span style="background:#43a047;color:white;border-radius:50%;'
                                f'padding:0 0.35rem;font-size:0.7rem;margin-right:0.4rem;">{i+1}</span>'
                                f'「{g_orig}」'
                                f'</div>'
                                f'<div style="color:#5d3700;margin:0.15rem 0;"><b>Issue：</b>{g_detail}</div>'
                                f'<div style="color:#1b5e20;"><b>Suggestion：</b>{g_sugg}</div>'
                                '</div>'
                            )

                    right_parts.append('</div>')  # close right-fb
                    st.markdown(''.join(right_parts), unsafe_allow_html=True)

                    # ─────── 结构内容批改 — 也在右栏内,需要 Streamlit 原生支持语音 ───────
                    if struct_iss:
                        for si_idx, si in enumerate(struct_iss):
                            si_aspect = si.get('aspect', '')
                            si_problem = si.get('problem', '')
                            si_sugg = si.get('suggestion', '')
                            si_example = si.get('example', '')
                            si_voice_zh = si.get('voice_zh', '')
                            si_voice_en = si.get('voice_en', '')

                            # 蓝色卡片(问题 + 建议 + 范例)
                            si_html = (
                                '<div style="background:#e3f2fd;border-radius:5px;'
                                'padding:0.5rem 0.7rem;margin:0.3rem 0;font-size:0.85rem;'
                                'border-left:3px solid #1565c0;">'
                                f'<div style="color:#0d47a1;font-weight:600;margin-bottom:0.3rem;font-size:0.85rem;">'
                                f'📐 {html_escape(si_aspect)}</div>'
                                f'<div style="color:#5d3700;margin:0.2rem 0;"><b>Issue：</b>{html_escape(si_problem)}</div>'
                                f'<div style="color:#1b5e20;margin:0.2rem 0;"><b>Suggestion：</b>{html_escape(si_sugg)}</div>'
                            )
                            if si_example:
                                si_html += (
                                    '<div style="background:white;border-radius:4px;'
                                    'padding:0.4rem 0.6rem;margin-top:0.3rem;border:1px solid #c5d4e3;'
                                    'font-size:0.82rem;">'
                                    '<b style="color:#0d47a1;">Example：</b>'
                                    f'<span style="color:#2c2c2a;line-height:1.6;">{html_escape(si_example)}</span>'
                                    '</div>'
                                )
                            si_html += '</div>'
                            st.markdown(si_html, unsafe_allow_html=True)

                            # 中英文语音按钮 — 紧凑型,放在卡片下方
                            if si_voice_zh or si_voice_en:
                                v_col1, v_col2 = st.columns(2)
                                with v_col1:
                                    if si_voice_zh:
                                        with st.expander("🔊 中文讲解", expanded=False):
                                            try:
                                                import asyncio, edge_tts, io as _io
                                                async def _gen_zh(text):
                                                    com = edge_tts.Communicate(
                                                        text, voice="zh-CN-XiaoxiaoNeural", rate="-5%"
                                                    )
                                                    buf = _io.BytesIO()
                                                    async for c in com.stream():
                                                        if c["type"] == "audio": buf.write(c["data"])
                                                    buf.seek(0); return buf
                                                st.audio(
                                                    asyncio.run(_gen_zh(si_voice_zh)),
                                                    format="audio/mp3"
                                                )
                                                st.caption(si_voice_zh)
                                            except Exception as e:
                                                st.caption(f"语音不可用：{e}")
                                                st.write(si_voice_zh)
                                with v_col2:
                                    if si_voice_en:
                                        with st.expander("🔊 English", expanded=False):
                                            try:
                                                import asyncio, edge_tts, io as _io
                                                async def _gen_en(text):
                                                    com = edge_tts.Communicate(
                                                        text, voice="en-US-JennyNeural", rate="-5%"
                                                    )
                                                    buf = _io.BytesIO()
                                                    async for c in com.stream():
                                                        if c["type"] == "audio": buf.write(c["data"])
                                                    buf.seek(0); return buf
                                                st.audio(
                                                    asyncio.run(_gen_en(si_voice_en)),
                                                    format="audio/mp3"
                                                )
                                                st.caption(si_voice_en)
                                            except Exception as e:
                                                st.caption(f"Audio unavailable: {e}")
                                                st.write(si_voice_en)

                    # ── 段落级基础/进阶版按钮 + 修改示范 (放在右栏内部底部) ──
                    ver_key = f"para_ver_{para_num}"
                    if ver_key not in st.session_state:
                        st.session_state[ver_key] = "basic"

                    # 分隔线
                    st.markdown(
                        '<div style="border-top:1px dashed #d4e3f5;margin:0.8rem 0 0.5rem;"></div>',
                        unsafe_allow_html=True
                    )

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(
                            "📘 基础版" + (" ✓" if st.session_state[ver_key]=="basic" else ""),
                            key=f"btn_b_{para_num}", use_container_width=True
                        ):
                            st.session_state[ver_key] = "basic"
                            st.rerun()
                    with btn_col2:
                        if st.button(
                            "🌟 进阶版" + (" ✓" if st.session_state[ver_key]=="advanced" else ""),
                            key=f"btn_a_{para_num}", use_container_width=True
                        ):
                            st.session_state[ver_key] = "advanced"
                            st.rerun()

                    # 显示选中的版本修改
                    cur_ver = st.session_state[ver_key]
                    cur_revised = revised_b if cur_ver == "basic" else revised_a
                    ver_color = "#558b2f" if cur_ver == "basic" else "#6a1b9a"
                    ver_bg = "#f1f8e9" if cur_ver == "basic" else "#f3e5f5"
                    ver_label = "Basic (小六水平)" if cur_ver == "basic" else "Advanced (A1+水平)"

                    st.markdown(
                        f'<div style="background:{ver_bg};border-left:3px solid {ver_color};'
                        f'padding:0.7rem 0.9rem;margin:0.4rem 0 0;border-radius:5px;">'
                        f'<div style="color:{ver_color};font-weight:500;font-size:0.78rem;'
                        f'margin-bottom:0.3rem;">📝 {ver_label}</div>'
                        f'<div style="color:#2c2c2a;font-size:0.88rem;line-height:1.8;">'
                        f'{html_escape(cur_revised)}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            # 段落间距
            st.markdown('<div style="margin-bottom:1.5rem;"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # 模块 5:整篇范文 + 原文对比
    # ══════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    if paragraphs:
        student_full_text = st.session_state.get('ocr_text', '')

        # 整篇范文的独立切换
        if 'model_essay_ver' not in st.session_state:
            st.session_state['model_essay_ver'] = 'basic'

        st.markdown("### 📖 整篇范文对比")
        m_col1, m_col2, _ = st.columns([1, 1, 4])
        with m_col1:
            if st.button(
                "📘 基础版" + (" ✓" if st.session_state['model_essay_ver']=='basic' else ""),
                key="model_essay_b", use_container_width=True
            ):
                st.session_state['model_essay_ver'] = 'basic'
                st.rerun()
        with m_col2:
            if st.button(
                "🌟 进阶版" + (" ✓" if st.session_state['model_essay_ver']=='advanced' else ""),
                key="model_essay_a", use_container_width=True
            ):
                st.session_state['model_essay_ver'] = 'advanced'
                st.rerun()

        m_ver = st.session_state['model_essay_ver']
        full_model = model_basic if m_ver == 'basic' else model_advanced
        version_name = "基础版" if m_ver == 'basic' else "进阶版"

        if full_model:
            model_color = "#558b2f" if m_ver == 'basic' else "#6a1b9a"
            model_bg = "#f1f8e9" if m_ver == 'basic' else "#f3e5f5"

            col_orig, col_revised = st.columns(2)
            with col_orig:
                st.markdown(
                    '<div style="background:#fafaf0;border-left:4px solid #888;'
                    'padding:1rem 1.2rem;border-radius:8px;font-size:0.92rem;'
                    'line-height:1.85;color:#2c2c2a;white-space:pre-wrap;'
                    'min-height:300px;">'
                    '<div style="font-size:0.8rem;color:#666;font-weight:600;margin-bottom:0.6rem;">'
                    '📝 你的原文'
                    '</div>'
                    f'{html_escape(student_full_text)}'
                    '</div>',
                    unsafe_allow_html=True
                )
            with col_revised:
                st.markdown(
                    f'<div style="background:{model_bg};border-left:4px solid {model_color};'
                    'padding:1rem 1.2rem;border-radius:8px;font-size:0.92rem;'
                    'line-height:1.85;color:#2c2c2a;white-space:pre-wrap;'
                    'min-height:300px;">'
                    f'<div style="font-size:0.8rem;color:{model_color};font-weight:600;margin-bottom:0.6rem;">'
                    f'✨ {version_name}范文'
                    '</div>'
                    f'{html_escape(full_model)}'
                    '</div>',
                    unsafe_allow_html=True
                )
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
