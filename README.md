# 华文作文批改平台 v2.0

新加坡中学华文作文 AI 批改系统 — **基于 SEAB 官方评分标准**。

## v2.0 主要升级

相比 v1.0，本版本做了以下关键改进：

### 1. 嵌入 SEAB 官方评分标准
- 中学高级华文（HCL）— 60 分制
- 中学普通华文 O 水准（CL 1160）— 40 分制
- 中学普通华文 N 水准（CL 1196）— 40 分制
- 中学实用文 O / N 水准 — 20 分制

每个考试段的官方等级描述（"第 1 等级 24-30 分"等）直接嵌入在 AI prompt 中，
确保 AI 严格按官方标准评分，而不是凭感觉打分。

### 2. AI 必须给出评分依据
新增 `grading_rationale` 字段，AI 必须说明：
- 内容定为第几等级、依据是什么（必须引用原文）
- 语文定为第几等级、依据是什么（必须引用原文）

### 3. 等级估算 + 距离下一档
- 60 分制 → A1/A2/B3/B4/C5/C6 等级换算
- 自动计算"距离下一档差几分，怎么改进"

### 4. 老师创建题目时只需选考试段
不需要手动写 rubric，系统自动套用 SEAB 官方标准。
老师只需补充本次教学的特别要求即可。

## 文件结构

```
essay-grader-v2/
├── prompts.py        ← 新增：SEAB 评分标准 prompt 引擎（核心）
├── database.py       ← 修改：assignments 表加入 exam_level 字段
├── app.py            ← 不变
├── pages/
│   ├── student.py    ← 修改：使用新的 prompt 引擎
│   ├── admin.py      ← 修改：加入考试段选择
│   └── progress.py   ← 不变
└── requirements.txt  ← 不变
```

## 部署

1. 安装依赖：`pip install -r requirements.txt`
2. 在 Streamlit Cloud 的 secrets 中设置 `ANTHROPIC_API_KEY`
3. 运行：`streamlit run app.py`

## 向后兼容

旧的 assignments（没有 exam_level 字段）会自动使用 HCL 标准。
