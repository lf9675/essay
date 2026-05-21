# -*- coding: utf-8 -*-
"""
CLever 华文通 · 理解二导师 (pages/lijie2.py)
=============================================
六步引导流程：拆段 → 标中心 → 预测考点 → 出题/上传真题 → 引导答题 → 四色对比 → 答题模板

【工程规范（与刘老师 CLever 仓库一致）】
- 所有 AI 调用用 client.messages.stream()，不可用 create()
- 四层 JSON 防御：直接解析 → 清洗 markdown → 修引号换行 → 截断/正则兜底
- .block-container padding-top: 3.5rem 防工具栏遮挡
- 用 st.container(border=True)，不用 HTML <div> 包裹 columns
- HTML 用单行字符串拼接，不用 f-string 多行（避免渲染成代码块）
- API key 存 Streamlit Secrets（沿用 "zuowenzhidao"）
- 修改 AI 输出字段时，务必同步更新 prompts_lijie2.py
"""

import json
import re
import streamlit as st
from anthropic import Anthropic

import prompts_lijie2 as P   # 部署时按仓库结构调整为 from .. import 或 sys.path

# ----------------------------------------------------------------
# 页面基础设置
# ----------------------------------------------------------------
st.set_page_config(page_title="理解二导师 · 华文通", page_icon="📖", layout="wide")

# 防 Streamlit 工具栏遮挡 + 红/绿/▲ 标注配色（沿用 CLever 的红绿语义）
st.markdown(
    "<style>"
    ".block-container{padding-top:3.5rem;}"
    ".hl-center{background:#fde68a;padding:1px 4px;border-radius:3px;font-weight:600;}"
    ".hl-turn{color:#dc2626;font-weight:700;}"
    ".tag-chip{display:inline-block;background:#e0f2fe;color:#0369a1;"
    "padding:2px 10px;border-radius:12px;font-size:0.85rem;margin:2px;}"
    ".ok{color:#16a34a;font-weight:700;}.mid{color:#ca8a04;font-weight:700;}"
    ".bad{color:#dc2626;font-weight:700;}"
    "</style>",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------
# AI 调用：流式 + 四层 JSON 防御
# ----------------------------------------------------------------
def get_client():
    return Anthropic(api_key=st.secrets["zuowenzhidao"])


def call_ai_stream(prompt, max_tokens=4000):
    """流式调用，返回完整文本。大 max_tokens 必须流式，否则报 10 分钟超时。"""
    client = get_client()
    chunks = []
    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            chunks.append(text)
    return "".join(chunks)


def safe_json(raw):
    """四层 JSON 防御：保证永远拿到 dict，不显示空白错误页。"""
    if not raw:
        return None
    # 第 1 层：直接解析
    try:
        return json.loads(raw)
    except Exception:
        pass
    # 第 2 层：剥离 markdown 代码块与前后噪声
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    m = re.search(r"\{.*\}", cleaned, re.S)
    if m:
        cleaned = m.group(0)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # 第 3 层：修中文引号 / 多余换行
    fixed = cleaned.replace("“", '"').replace("”", '"').replace("\n", " ")
    try:
        return json.loads(fixed)
    except Exception:
        pass
    # 第 4 层：正则兜底——逐键抓取，至少不崩
    try:
        result = {}
        for key in re.findall(r'"(\w+)"\s*:', fixed):
            mm = re.search(r'"' + key + r'"\s*:\s*"([^"]*)"', fixed)
            if mm:
                result[key] = mm.group(1)
        return result if result else None
    except Exception:
        return None


def ai_json(prompt, max_tokens=4000):
    raw = call_ai_stream(prompt, max_tokens)
    data = safe_json(raw)
    if data is None:
        st.error("AI 返回解析失败，请重试一次。")
        st.stop()
    return data


# ----------------------------------------------------------------
# Session 状态
# ----------------------------------------------------------------
def init_state():
    for k, v in {
        "article": "", "segment": None, "predict": None,
        "questions": None, "guide": {}, "compare": {},
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

st.title("📖 理解二导师")
st.caption("CLever · 华文通家族　|　拆段 → 标中心 → 预测考点 → 引导答题 → 四色对比 → 答题模板")


# ================================================================
# 步骤 0：篇章进入（粘贴 / 拍照上传）
# ================================================================
with st.container(border=True):
    st.subheader("第一步　放入篇章")
    tab_paste, tab_photo = st.tabs(["✍️ 粘贴文字", "📷 拍照上传真题"])

    with tab_paste:
        txt = st.text_area("把篇章粘贴进来", value=st.session_state.article, height=220,
                           placeholder="粘贴一篇高级华文理解二的篇章……")
        if st.button("确定使用这篇文字", key="use_paste"):
            st.session_state.article = txt.strip()
            st.session_state.segment = None
            st.success("篇章已载入。")

    with tab_photo:
        img = st.file_uploader("上传真题照片（JPG / PNG）", type=["jpg", "jpeg", "png"])
        if img and st.button("识别照片中的篇章", key="use_photo"):
            import base64
            b64 = base64.b64encode(img.read()).decode()
            media = "image/png" if img.type.endswith("png") else "image/jpeg"
            client = get_client()
            with st.spinner("正在识别篇章文字……"):
                chunks = []
                with client.messages.stream(
                    model="claude-sonnet-4-20250514", max_tokens=3000,
                    messages=[{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64",
                         "media_type": media, "data": b64}},
                        {"type": "text", "text": "请只输出图片中的篇章正文文字，"
                         "保留分段，不要加任何说明、标题或编号。"},
                    ]}],
                ) as stream:
                    for t in stream.text_stream:
                        chunks.append(t)
                st.session_state.article = "".join(chunks).strip()
                st.session_state.segment = None
            st.success("识别完成，可在「粘贴文字」标签里查看 / 修改。")

article = st.session_state.article
if not article:
    st.info("先放入一篇篇章，再开始引导。")
    st.stop()


# ================================================================
# 步骤 1+2：拆解段落 + 标注中心
# ================================================================
with st.container(border=True):
    st.subheader("第二步　拆解段落 + 标注中心")
    if st.button("🔍 开始拆解 + 标中心", key="seg"):
        with st.spinner("正在拆段、找中心、标转折……"):
            st.session_state.segment = ai_json(P.prompt_segment_and_center(article), 3000)

    seg = st.session_state.segment
    if seg:
        st.markdown("**全文中心：**　" + seg.get("main_idea", ""))
        st.markdown("**大层次：**　" + seg.get("layers", ""))
        for p in seg.get("paragraphs", []):
            chip = "<span class='tag-chip'>第" + str(p.get("num", "")) + "段　" + p.get("label", "") + "</span>"
            line = chip
            if p.get("center_sentence"):
                line += "　中心句：<span class='hl-center'>" + p["center_sentence"] + "</span>"
            if p.get("has_turn"):
                line += "　<span class='hl-turn'>▲转折：" + p.get("turn_word", "") + "</span>"
            st.markdown(line, unsafe_allow_html=True)
        if seg.get("reading_tip"):
            st.info("💡 " + seg["reading_tip"])


# ================================================================
# 步骤 3：预测考点
# ================================================================
with st.container(border=True):
    st.subheader("第三步　预测考点（四问扫描）")
    if st.button("🎯 预测这篇会怎么考", key="pred"):
        with st.spinner("正在用四问扫描法预测考点……"):
            st.session_state.predict = ai_json(P.prompt_predict(article), 2500)

    pr = st.session_state.predict
    if pr:
        for i, item in enumerate(pr.get("predictions", []), 1):
            with st.container(border=True):
                st.markdown("**考点 " + str(i) + "　[" + item.get("type", "") + "]**")
                st.markdown("位置：" + item.get("location", ""))
                st.markdown("为什么会考：" + item.get("why", ""))
                st.markdown("很可能这样问：*" + item.get("likely_question", "") + "*")


# ================================================================
# 步骤 4：出题（AI 自动出题 / 用真题）
# ================================================================
with st.container(border=True):
    st.subheader("第四步　练习题目")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🤖 AI 仿真题自动出 5 题", key="gen"):
            with st.spinner("正在仿 O 水准题型命题……"):
                st.session_state.questions = ai_json(P.prompt_generate_questions(article), 5000).get("questions")
    with c2:
        st.caption("或在下方手动贴入真题题目，逐题引导 / 批改。")

    qs = st.session_state.questions
    if qs:
        for q in qs:
            with st.container(border=True):
                st.markdown("**第 " + str(q.get("num", "")) + " 题　(" + str(q.get("marks", "")) +
                            " 分)　[" + q.get("type", "") + "]**")
                st.markdown(q.get("question", ""))


# ================================================================
# 步骤 5：引导答题 + 步骤 6：四色对比
# ================================================================
with st.container(border=True):
    st.subheader("第五步　引导答题 + 第六步　四色对比标准答案")
    st.caption("选一道题，先看引导，写完答案后再让 AI 逐采分点对比。")

    qs = st.session_state.questions or []
    if qs:
        labels = ["第 " + str(q.get("num")) + " 题 [" + q.get("type", "") + "]" for q in qs]
        idx = st.selectbox("选择题目", range(len(qs)), format_func=lambda i: labels[i])
        cur = qs[idx]
        qkey = str(cur.get("num"))

        st.markdown("**题目：**　" + cur.get("question", ""))

        # 引导（不给答案）
        if st.button("🧭 先引导我思考（不给答案）", key="guide_" + qkey):
            with st.spinner("导师正在带你拆题……"):
                st.session_state.guide[qkey] = ai_json(
                    P.prompt_guide(article, cur.get("question", ""), cur.get("type", "")), 2000)
        g = st.session_state.guide.get(qkey)
        if g:
            st.markdown("**先数分：**　" + g.get("marks_hint", ""))
            for s in g.get("thinking_steps", []):
                st.markdown("- " + s)
            st.markdown("**去哪找：**　" + g.get("where_to_look", ""))
            st.markdown("**答题模板：**　`" + g.get("template", "") + "`")
            st.warning("⚠️ 易踩陷阱：" + g.get("trap", ""))

        # 学生作答 + 四色对比
        ans = st.text_area("✍️ 写下你的答案", key="ans_" + qkey, height=120)
        if st.button("🎨 四色对比标准答案", key="cmp_" + qkey):
            if not ans.strip():
                st.warning("先写下你的答案再对比。")
            else:
                with st.spinner("评卷员正在逐采分点批改……"):
                    st.session_state.compare[qkey] = ai_json(
                        P.prompt_compare(article, cur.get("question", ""),
                                         cur.get("model_answer", ""),
                                         cur.get("scoring_points", []), ans.strip()), 3000)
        cmp = st.session_state.compare.get(qkey)
        if cmp:
            st.markdown("### 得分：" + str(cmp.get("got_marks", "?")) + " / " + str(cmp.get("total_marks", "?")))
            for pt in cmp.get("point_check", []):
                status = pt.get("status", "")
                cls = "ok" if "✓" in status else ("mid" if "△" in status else "bad")
                line = "<span class='" + cls + "'>" + status + "</span>　" + pt.get("point", "")
                line += "　——" + pt.get("comment", "")
                if pt.get("from_text"):
                    line += "　〔原文：" + pt["from_text"] + "〕"
                st.markdown(line, unsafe_allow_html=True)
            if cmp.get("rule_flag"):
                st.error("🚨 触犯铁律：" + cmp["rule_flag"])
            if cmp.get("one_fix"):
                st.info("🎯 最该改进：" + cmp["one_fix"])
            if cmp.get("encouragement"):
                st.success("💪 " + cmp["encouragement"])
    else:
        st.caption("先在第四步出题，或贴入真题。")


# ================================================================
# 侧栏：新加坡式答题模板（零 API，随时查）
# ================================================================
with st.sidebar:
    st.header("🇸🇬 新加坡式答题模板")
    st.caption("随时查，零等待。")
    for name, t in P.SG_TEMPLATES.items():
        with st.expander(name):
            st.markdown("**思路：**　" + t["思路"])
            st.markdown("**模板：**　`" + t["模板"] + "`")
            st.markdown("**铁律：**　" + t["铁律"])
