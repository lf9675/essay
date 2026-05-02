"""
SEAB 官方评分标准嵌入式 Prompt 库
==================================

每个考试段对应一个 prompt 生成函数，确保 AI 严格按官方标准评分。

考试段：
- HCL (Higher Chinese Language) - 中学高级华文 - 60 分制
- O_CL (O-Level Chinese)        - 中学普通华文 O 水准 - 40 分制
- N_CL (N-Level Chinese)        - 中学普通华文 N(A) 水准 - 40 分制
- PRACTICAL (实用文)              - 中学实用文 - 20/10 分制
"""

# ════════════════════════════════════════════════════════════════════
# 考试段定义
# ════════════════════════════════════════════════════════════════════

EXAM_LEVELS = {
    "HCL": {
        "name": "中学高级华文（HCL）",
        "syllabus_code": "Higher Chinese Language",
        "essay_total": 60,
        "content_max": 30,
        "language_max": 30,
        "min_words": 500,
        "genres": ["记叙文", "议论文", "说明文"],
    },
    "O_CL": {
        "name": "中学普通华文 O 水准（CL 1160）",
        "syllabus_code": "1160",
        "essay_total": 40,
        "content_max": 20,
        "language_max": 20,
        "min_words": 300,
        "genres": ["记叙文", "议论文", "说明文"],
    },
    "N_CL": {
        "name": "中学普通华文 N(A) 水准（CL 1196）",
        "syllabus_code": "1196",
        "essay_total": 40,
        "content_max": 20,
        "language_max": 20,
        "min_words": 240,
        "genres": ["记叙文", "议论文", "说明文"],
    },
    "PRACTICAL_O": {
        "name": "中学普通华文 O 水准 实用文（CL 1160）",
        "syllabus_code": "1160-Practical",
        "essay_total": 20,
        "content_max": 10,
        "language_max": 10,
        "min_words": 150,
        "genres": ["电子邮件"],
    },
    "PRACTICAL_N": {
        "name": "中学普通华文 N(A) 水准 实用文（CL 1196）",
        "syllabus_code": "1196-Practical",
        "essay_total": 20,
        "content_max": 10,
        "language_max": 10,
        "min_words": 120,
        "genres": ["电子邮件"],
    },
}


# ════════════════════════════════════════════════════════════════════
# SEAB 官方评分标准 - 直接来自考评局文档
# ════════════════════════════════════════════════════════════════════

# ---- HCL 高级华文 60 分制（来自《中学高华_作文评分标准》）----

HCL_RUBRIC = """
═══ 中学高级华文作文评分标准（满分 60，字数 500 以上）═══

【内容评分指引（30 分）】

第 1 等级（24-30 分）— 充实、生动
• 充实度：选材有创意有意义、合乎生活逻辑、人物描写生动形象；说明详尽（写得多/具体）
• 相关性：切合题意，紧扣题目关键词，详略安排恰当，支持中心的内容详写
• 内容铺展：有层次、文章结构清楚、铺述清楚（背景/人物/相关情况清楚交代）、有条理、表达逻辑性强

第 2 上等级（20-23 分）— 相当充实
• 相当充实、生动，说明也相当详尽
• 相当切合题意
• 内容相当有层次，铺述相当清楚、有条理

第 2 下等级（16-19 分）— 还算充实
• 还算充实，说明也算详尽
• 还算切合题意，不过内容平淡
• 内容还算有层次，铺述还算清楚、有条理

第 3 上等级（12-15 分）— 不太充实
• 不太充实，说明也不太详尽
• 不太切合题意，而且内容很平淡
• 内容层次不太清楚、不太有条理

第 3 下等级（8-11 分）— 不足、空洞
• 不足、空洞
• 没有紧扣题意
• 内容层次不清楚，没有条理

第 4 等级（0-7 分）— 严重不足
• 非常不足、空洞
• 不切合题意，甚至离题
• 内容杂乱无章

【语文/结构评分指引（30 分）】

第 1 等级（24-30 分）— 优秀
• 结构和文法：语句通顺，汉字书写及标点符号运用正确，如有错误也是极小的；句式多样化且正确；结构严谨、条理分明、段落清楚
• 词汇：词汇丰富，用词很正确
• 格式或组织：格式正确；组织得当，衔接紧凑，表达通畅，意思清楚

第 2 上等级（20-23 分）— 相当好
• 结构和文法：语句大部分通顺，汉字书写及标点符号有些错误；句式有变化且相当正确；结构相当严谨
• 词汇：词汇足够，用词相当正确
• 格式或组织：格式相当正确；组织相当得当，衔接相当紧凑

第 2 下等级（16-19 分）— 还算可以
• 结构和文法：语句还算通顺，汉字书写及标点符号错误不少；句式简单，变化少；结构还算完整
• 词汇：词汇有限，用词还算正确
• 格式或组织：格式还算正确；组织还算得当，衔接还算紧凑

第 3 上等级（12-15 分）— 不太好
• 结构和文法：语句不太通顺，汉字书写及标点错误比较多；句式简单无变化，文法有错误；结构不太完整
• 词汇：词汇贫乏，用词不太正确
• 格式或组织：格式不太正确；组织不太得当，衔接不太紧凑

第 3 下等级（8-11 分）— 较差
• 结构和文法：语句欠通顺，汉字书写及标点错误多；句式简单，文法错误多；结构不完整
• 词汇：词汇贫乏，用词不准确
• 格式或组织：格式错误多；组织有点松散

第 4 等级（0-7 分）— 严重不足
• 结构和文法：语句完全不正确，汉字书写及标点错误非常多；文法错误很多；结构杂乱无章
• 词汇：词汇非常贫乏，用词错误连篇
• 格式或组织：格式错误很多；组织凌乱，完全没有衔接

【O-Level 等级换算】
• A1: 总分 45-60
• A2: 总分 42-44
• B3: 总分 39-41
• B4: 总分 36-38
• C5: 总分 33-35
• C6: 总分 30-32
• D7-F9: 总分 30 以下
"""


# ---- O-Level / N-Level 普通华文 40 分制（来自 1160 / 1196 syllabus）----

CL_RUBRIC_40 = """
═══ 中学普通华文作文评分标准（满分 40）═══

【内容评分指引（20 分）】

第 1 等级（17-20 分）
• 内容充实，切合题意
• 内容有层次，说明详尽、有条理

第 2 等级（13-16 分）
• 内容相当充实，相当切合题意
• 内容相当有层次，说明相当详尽，也相当有条理

第 3 等级（9-12 分）
• 内容还算充实，还算切合题意
• 内容还算有层次，说明还算详尽、有条理

第 4 等级（5-8 分）
• 内容不太充实，不太切合题意
• 内容层次不太清楚，说明也不太详尽、不太有条理

第 5 等级（1-4 分）
• 内容不足，不切合题意
• 内容层次不清楚，没有条理或重复，甚至杂乱无章

【语文与结构评分指引（20 分）】

第 1 等级（17-20 分）
• 语句通顺，汉字的书写、词语、语法及标点符号的运用绝大多数正确，如有错误也是极小的
• 用词丰富适当，句式正确且多样化，表达清楚
• 组织得当，衔接紧凑，段落分明

第 2 等级（13-16 分）
• 语句相当通顺，汉字书写、词语、语法及标点符号有一些小错误
• 用词适当，句式相当正确且有变化，表达相当清楚
• 组织相当得当，衔接相当紧凑，段落相当分明

第 3 等级（9-12 分）
• 语句还算通顺，汉字书写、词语、语法及标点符号有些错误
• 用词还算适当，句式简单变化少，表达还算清楚
• 组织还算得当，衔接还算紧凑，段落还算分明

第 4 等级（5-8 分）
• 语句不太通顺，汉字书写、词语及标点错误多
• 词汇有限，句式简单无变化，表达不太清楚
• 组织不太得当，衔接不太紧凑，段落不太分明

第 5 等级（1-4 分）
• 语句不通顺，汉字书写、词语、语法及标点错误非常多
• 词汇贫乏，遣词造句错误多，表达不清楚
• 组织凌乱，没有衔接
"""


# ---- 实用文 20 分制（O-Level / N-Level 共用）----

PRACTICAL_RUBRIC = """
═══ 中学实用文（电子邮件）评分标准（满分 20）═══

【内容评分指引（10 分）】

第 1 等级（9-10 分）
• 内容充实，切合题意
• 内容有层次，说明详尽、有条理

第 2 等级（6-8 分）
• 内容相当充实，相当切合题意
• 内容相当有层次，说明相当详尽，也相当有条理

第 3 等级（3-5 分）
• 内容不太充实，不太切合题意
• 内容层次不太清楚，说明也不太详尽、不太有条理

第 4 等级（1-2 分）
• 内容不足，不切合题意
• 内容层次不清楚，没有条理或重复，甚至杂乱无章

【语文与结构评分指引（10 分）】

第 1 等级（9-10 分）
• 语句通顺，汉字的书写、词语、语法及标点符号的运用绝大多数正确
• 语言表达清楚
• 组织得当，衔接紧凑，段落分明

第 2 等级（6-8 分）
• 语句相当通顺，汉字书写、词语、语法及标点有一些错误
• 语言表达相当清楚
• 组织相当得当，衔接相当紧凑

第 3 等级（3-5 分）
• 语句不太通顺，汉字书写、词语、语法及标点错误多
• 语言表达不太清楚，词语有限，句式简单无变化
• 组织不太得当，衔接不太紧凑

第 4 等级（1-2 分）
• 语句不通顺，错误非常多
• 语言表达不清楚，错误连篇
• 组织凌乱，没有衔接
"""


# ════════════════════════════════════════════════════════════════════
# Grade 估算函数 - 把分数转换为 O-Level 等级
# ════════════════════════════════════════════════════════════════════

def estimate_grade_hcl(total_score):
    """HCL 60 分制 → O-Level 等级"""
    if total_score >= 45: return "A1"
    if total_score >= 42: return "A2"
    if total_score >= 39: return "B3"
    if total_score >= 36: return "B4"
    if total_score >= 33: return "C5"
    if total_score >= 30: return "C6"
    if total_score >= 25: return "D7"
    if total_score >= 20: return "E8"
    return "F9"


def estimate_grade_cl(total_score, max_score=40):
    """普通华文 40 分制 → O/N-Level 等级（按比例换算）"""
    pct = (total_score / max_score) * 100
    if pct >= 75: return "A1"
    if pct >= 70: return "A2"
    if pct >= 65: return "B3"
    if pct >= 60: return "B4"
    if pct >= 55: return "C5"
    if pct >= 50: return "C6"
    if pct >= 45: return "D7"
    if pct >= 40: return "E8"
    return "F9"


def grade_distance_hcl(total_score):
    """计算到下一档（更高一级）的距离 - HCL"""
    # 从低到高排列，找出第一个比当前分数高的等级
    targets_asc = [
        ("D7", 25), ("C6", 30), ("C5", 33),
        ("B4", 36), ("B3", 39), ("A2", 42), ("A1", 45)
    ]
    for grade, threshold in targets_asc:
        if total_score < threshold:
            return {"next_grade": grade, "points_needed": threshold - total_score}
    return {"next_grade": "已达最高 A1", "points_needed": 0}


# ════════════════════════════════════════════════════════════════════
# 核心 Prompt 生成函数
# ════════════════════════════════════════════════════════════════════

def build_grading_prompt(exam_level, genre, prompt_text, requirements,
                          focus_areas=None, custom_rubric=None):
    """
    生成针对特定考试段的批改 system prompt

    参数：
        exam_level: "HCL" / "O_CL" / "N_CL" / "PRACTICAL_O" / "PRACTICAL_N"
        genre: "记叙文" / "议论文" / "说明文" / "电子邮件"
        prompt_text: 作文题目
        requirements: 老师的写作要求
        focus_areas: 老师勾选的批改焦点列表
        custom_rubric: 老师自定义的额外标准（可选，附加在官方标准之后）
    """

    if exam_level not in EXAM_LEVELS:
        raise ValueError(f"未知考试段：{exam_level}")

    config = EXAM_LEVELS[exam_level]

    # 选择对应的官方评分标准
    if exam_level == "HCL":
        official_rubric = HCL_RUBRIC
    elif exam_level in ("O_CL", "N_CL"):
        official_rubric = CL_RUBRIC_40
    elif exam_level in ("PRACTICAL_O", "PRACTICAL_N"):
        official_rubric = PRACTICAL_RUBRIC
    else:
        official_rubric = ""

    # 根据文体选择评分维度（细分维度，便于学生理解）
    if genre == "议论文":
        sub_dims = ["论点清晰度", "论据充分性", "论证逻辑", "结构组织", "语言表达"]
    elif genre == "说明文":
        sub_dims = ["说明顺序", "说明方法", "语言准确性", "结构组织", "语言表达"]
    elif genre == "电子邮件":
        sub_dims = ["格式正确性", "语气得体性", "内容切题", "结构条理", "语言表达"]
    else:  # 记叙文
        sub_dims = ["内容主题", "情节结构", "人物描写", "语言表达", "开头结尾"]

    sub_dims_str = ", ".join([f'"{d}": 0到10的整数' for d in sub_dims])

    # 焦点批改指令
    focus_instruction = ""
    focus_feedback_format = '  "focus_feedback": [],'
    if focus_areas:
        focus_str = "、".join(focus_areas)
        focus_items = "\n".join([
            f'      {{"focus": "{f}", "rating": "好/一般/需改进", "comment": "针对这个方面的具体反馈（30字内）", "suggestion": "具体改进建议（30字内）"}}'
            for f in focus_areas
        ])
        focus_instruction = f"\n\n【本次批改重点】老师要求针对以下每一个方面都必须给出专门反馈，缺一不可：{focus_str}。每个焦点必须在 focus_feedback 里出现。"
        focus_feedback_format = f'  "focus_feedback": [\n{focus_items}\n  ],'

    # 拆解写作要求
    import re
    req_lines = []
    if requirements:
        req_text = re.sub(r'[（(]\d+[）)]', ';', requirements)
        req_text = req_text.replace('；', ';').replace('\n', ';')
        req_lines = [r.strip().lstrip('；;，,、') for r in req_text.split(';')
                     if r.strip() and len(r.strip()) > 3]

    if req_lines:
        req_items_str = "\n".join([f"  {i+1}. {r}" for i, r in enumerate(req_lines)])
        req_count = len(req_lines)
    else:
        req_items_str = "（按文体一般标准批改）"
        req_count = 1

    # 自定义补充标准
    custom_section = f"\n\n【老师补充标准】\n{custom_rubric}" if custom_rubric else ""

    # ─────────────────────────────────────────────────────
    # 拼接完整 system prompt
    # ─────────────────────────────────────────────────────
    system_prompt = f"""你是新加坡考评局（SEAB）认证级别的{config['name']}作文评分员。你必须严格按照下方的考评局官方评分指引评分，不能凭感觉打分。

═══════════════════════════════════════════════════════
{official_rubric}
═══════════════════════════════════════════════════════
{custom_section}

【评分铁律 - 必须遵守】

1. 内容分（满分 {config['content_max']}）和语文分（满分 {config['language_max']}）必须分别参照上方官方等级描述判定，不能笼统打分。

2. 评分时必须先确定属于哪个"等级"（如第 1 等级 / 第 2 上 / 第 2 下…），再在该等级的分数区间内取值。

3. 必须在 grading_rationale 字段说明：内容定为第几等级（依据是什么），语文定为第几等级（依据是什么）。

4. 字数低于 {config['min_words']} 字的作文，内容分最高只能给到第 3 上等级。

5. 学生华文程度普遍中等，反馈语言要鼓励为主，但分数必须客观。绝不可为了鼓励而虚报分数。

{focus_instruction}

【核心任务：必须逐一批改以下写作要求】
{req_items_str}

每条要求必须：判断"做到了/部分做到/没做到"，引用原文分析（用【】括起原文），没做到须给修改例子。

【输出格式 - 严格按以下 JSON，不要加任何其他文字或 markdown】

{{
  "scores": {{
    "content": 内容分整数（0-{config['content_max']}）,
    "language": 语文分整数（0-{config['language_max']}）,
    "total": 总分整数（content + language）,
    "sub_scores": {{{sub_dims_str}}}
  }},
  "grading_rationale": {{
    "content_level": "第X等级（X-X分区间）",
    "content_reason": "为什么定为这个等级，引用原文证据用【】括起",
    "language_level": "第X等级（X-X分区间）",
    "language_reason": "为什么定为这个等级，引用原文证据用【】括起"
  }},
  "grade_estimate": "如B4",
  "grade_distance": "距离下一档（如B3）还差几分，怎么改进可以达到",
  "audio_script": "口语总评约80字",
  "strengths": ["具体优点1（要引用原文）", "具体优点2（要引用原文）"],
{focus_feedback_format}
  "requirements_feedback": [
    {{"req_num": 1, "achieved": "做到了/部分做到/没做到", "analysis": "分析内容，引用原文用【】括起来", "example": "如未达成，给修改例子"}}
  ],
  "issues": {{
    "language": [{{"location":"第X段第Y句","original":"原句","improved":"改后","explanation":"原因"}}],
    "structure": [{{"location":"第X段","problem":"问题","suggestion":"建议"}}],
    "content": [{{"location":"第X段","problem":"问题","suggestion":"建议"}}]
  }},
  "highlight_errors": [
    {{"text":"错别字或病句原文（要和作文里完全一样）","type":"问题","improved":"正确写法"}}
  ],
  "upgrade_table": [{{"original":"弱句","level3":"优秀版"}}],
  "overall_suggestion": "最重要建议30字内",
  "encouragement": "鼓励一句",
  "model_essay_paragraphs": [
    {{"original": "第1段原文（完整复制）", "revised": "第1段修改版，改动处用**加粗**标记"}}
  ]
}}

【字段规则】

1. requirements_feedback 必须有 {req_count} 条，每条 req_num 对应写作要求编号。
2. achieved 只填三个词之一：做到了、部分做到、没做到。
3. 【严禁】所有字符串值内部不能出现英文双引号"，引用原文必须用【】括起来。
4. language/structure/content 各最多 3 条，没问题就填 []。
5. upgrade_table 最多 3 句；strengths 最多 2 条。
6. highlight_errors 必须找出作文里所有错别字和病句弱句，text 必须和原文完全一致（包括标点）用于高亮定位。
7. model_essay_paragraphs 必须覆盖所有段落，revised 总字数最少 {config['min_words']} 字，改动处用 **加粗** 标记。revised 里对话用『』而不是英文引号。
8. grading_rationale 是核心字段，必须严格对应官方等级描述，不能模糊。"""

    return system_prompt


def build_user_message(prompt_text, requirements, genre, essay_text):
    """生成 user message"""
    return f"""题目：{prompt_text}
写作要求：{requirements}
文体：{genre}

以下是学生的作文（经过 OCR 识别，学生已核对）：

{essay_text}"""
