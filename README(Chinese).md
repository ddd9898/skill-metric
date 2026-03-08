[中文](README(Chinese).md) | [English](README.md)

# Skill Metric — Skill 质量评价工具

本 skill 的评价指标依据 Anthropic 官方文档 [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) 所总结。

---

`skill-metric` 是一个对 Agent Skill 做**静态质量评价**的工具 Skill，会对指定的 skill 目录打出三项得分：

- **2.1.1 Format**（格式）
- **2.1.2 Completeness**（完整性）
- **2.1.3 Writing**（写作）

三项分别满分 8 分，总分最高 **24 分**，并支持 **文本报告、JSON、CSV 以及单 skill 雷达图** 输出。

底层实现脚本位于 `skill-metric/scripts/skill_quality_eval.py`。

---

## 适用场景

- **批量检查 skills 质量**：对 `skills/` 目录下的一批 skills 做体检，找出格式或内容不达标的技能。
- **单个 skill 质量审计**：想要给某个 skill 做 Format / Completeness / Writing 的详细打分与说明。
- **导出结构化结果**：需要把结果导出成 **CSV 或 JSON**，用于统计、可视化或后续自动处理。
- **生成雷达图报告**：对单个 skill 生成 Format/Completeness/Writing 三维的雷达图，方便展示或写报告。

---

## 依赖

- **Python**：推荐 Python 3.10+。
- **第三方库**：
  - 基础打分逻辑只依赖标准库。
  - 使用 `--figure` 生成雷达图时需安装：`pip install matplotlib`。

---

## 命令行用法

推荐通过 `skill-metric/scripts/skill_quality_eval.py` 调用：

```bash
python skill-metric/scripts/skill_quality_eval.py <skill_path> [skill_path ...] [选项]
```

### 参数

| 参数 | 说明 |
|------|------|
| `skill_path` | 一个或多个 skill 目录路径，或对应的 `SKILL.md` 路径。例如：`skills/uniprot-database` 或 `skills/uniprot-database/SKILL.md` |

**注意**：路径必须指向「skill 目录」或该目录下的 `SKILL.md`，不要把 `skills/` 父目录本身当作一个 skill 传入（会被当成名为 `skills` 的单一 skill）。

### 选项

| 选项 | 说明 |
|------|------|
| `-q`, `--quiet` | 只打印总分，不展开各检查项详情 |
| `-j`, `--json` | 输出 JSON（多 skill 为数组，单 skill 为单个对象） |
| `--csv` [文件] | 输出 CSV。不写文件路径则输出到 stdout；写路径则保存到该文件 |
| `--figure` [文件] | **仅当评价一个 skill 时** 生成雷达图。不写路径则保存为 `<skill_name>_radar.png`；写路径则保存到该文件（需安装 matplotlib） |

---

## 使用示例

```bash
# 评价单个 skill，打印完整报告
python skill-metric/scripts/skill_quality_eval.py skills/uniprot-database

# 评价单个 skill，只显示总分
python skill-metric/scripts/skill_quality_eval.py skills/uniprot-database -q

# 评价单个 skill 并生成雷达图（默认保存为 <skill_name>_radar.png）
python skill-metric/scripts/skill_quality_eval.py skills/uniprot-database --figure

# 评价单个 skill 并指定雷达图输出路径
python skill-metric/scripts/skill_quality_eval.py skills/uniprot-database --figure report/radar.png

# 批量评价 skills 目录下所有 skill
python skill-metric/scripts/skill_quality_eval.py skills/*/

# 批量评价并输出 CSV（写入文件）
python skill-metric/scripts/skill_quality_eval.py skills/*/ --csv skill_scores.csv

# 批量评价并输出 CSV 到 stdout（可重定向）
python skill-metric/scripts/skill_quality_eval.py skills/*/ --csv > report.csv

# 输出 JSON
python skill-metric/scripts/skill_quality_eval.py skills/uniprot-database -j
python skill-metric/scripts/skill_quality_eval.py skills/*/ -j
```

---

## 评分体系总览（24 分）

完整评分细则见 `skill-metric/references/scoring_criteria.md`，这里给出总览：

| 维度 | 检查内容（摘要） | 满分 |
|------|------------------|------|
| **2.1.1 Format** | SKILL.md 是否存在且命名正确、目录名规则、YAML frontmatter、`name`/`description` 字段合法性等；每违反一项 -1 | 8 |
| **2.1.2 Completeness** | `license`、`compatibility`、`metadata` 是否填写，是否有 `scripts/`、`references/`、`assets/`，是否提供示例与错误处理说明；每满足一项 +1 | 8 |
| **2.1.3 Writing** | 是否有清晰的任务边界与触发条件、是否采用渐进式披露（正文 ≤ 5000 字符）、是否主要为英文、正文与目录引用是否一致、license 是否非占位、是否有版本信息等；每满足一项 +1 | 8 |

### 关键打分细则

**2.1.1 格式审查（满分 8 分，每违反一项扣 1 分）**

1. 必须有 `[skill_name]/SKILL.md` 文件，且必须命名为 `SKILL.md`（`skill.md`、`SKILL.MD` 等均不合格）。
2. `[skill_name]` 目录名不得包含空格、下划线；单词间用连字符，如 `notion-project-setup` ✓，`NotionProjectSetup` ✗。
3. `[skill_name]/` 内不要有 `README.md` 文件。
4. `SKILL.md` 内必须有 YAML frontmatter，且用 `---` 分隔。
5. frontmatter 必须包含 `name` 字段，且与目录名 `[skill_name]` 完全一致。
6. frontmatter 必须包含 `description` 字段，说明：a) 该 skill 做什么（what），b) 什么时候用（when）。
7. `description` 字段长度须少于 1024 字符。
8. `description` 字段不得包含 XML 标签（如 `<a>`）。

**2.1.2 内容完整性（基础分 0 分，每满足一项加 1 分）**

1. 是否有 `license` 字段？
2. 是否有 `compatibility` 字段（≤500 字符描述环境要求）？
3. 是否有 `metadata` 字段（作者、版本等）？
4. 是否有 `[skill_name]/scripts/` 子目录（且含至少一个文件）？
5. 是否有 `[skill_name]/references/` 子目录（且含至少一个文件）？
6. 是否有 `[skill_name]/assets/` 子目录（且含至少一个文件）？
7. `SKILL.md` 正文是否提供具体案例（如代码块或示例段落）？
8. `SKILL.md` 正文是否说明错误/异常处理方式？

**2.1.3 写作质量（基础分 0 分，每满足一项加 1 分）**

1. `description` 是否有明确任务边界？（如 “Analyzes Figma design files and generates developer handoff documentation.” ✓，“Helps with projects.” ✗）
2. `description` 是否有明确触发信号？（如 “Use when user uploads .fig files.”）
3. 是否实现渐进式披露：`SKILL.md` 正文 ≤5000 字，细节放在 `references/`，可执行代码放在 `scripts/`。
4. 主要内容是否以英文为主？
5. 引用与目录一致：正文中出现的 `references/` 或 `scripts/` 路径，对应文件是否存在？
6. 反向一致：若存在 `references/` 或 `scripts/` 目录，正文是否至少引用其中 1 个文件？
7. `license` 是否为非占位值？（排除 "Unknown"、空、"N/A" 等）
8. 是否有版本信息？（frontmatter 或正文中的库/数据版本，如 “Biopython 1.85”）

---

## 输出说明

### 文本报告（默认）

- 每个 skill 一段：技能名、路径、Format / Completeness / Writing 分数与总分。
- 若未使用 `-q`，会列出每条检查项的 ✓/✗ 以及对应说明，便于定位问题。

### JSON（`-j`）

- 单 skill：一个对象，包含 `skill_name`、`skill_dir`、`format_score`、`completeness_score`、`writing_score`、`total_score`，以及 `details`（按 format/completeness/writing 分类列出每条检查的 pass 与 message）。
- 多 skill：上述对象的数组，方便在其他程序中做进一步统计与可视化。

### CSV（`--csv`）

- **列**：`skill_name`、`skill_dir`（相对当前工作目录）、`format_score`、`completeness_score`、`writing_score`、`total_score`、`error`，以及 `format_1`…`format_8`、`completeness_1`…`completeness_8`、`writing_1`…`writing_8`（每条为 `PASS: 说明` 或 `FAIL: 说明`）。
- 一行一个 skill，适合在 Excel、数据仓库或其他分析脚本中做聚合和筛选。

### 雷达图（`--figure`）

- 仅在**评价一个 skill** 且该 skill 评价成功时生成。
- 三个轴：Format (2.1.1)、Completeness (2.1.2)、Writing (2.1.3)，刻度范围 0–8；标题会显示技能名和总分。
- 多 skill 场景下使用 `--figure` 会提示仅支持单 skill。

---

## 从 Python 调用

当你在 Python 里用 `subprocess` 调用该脚本时，需要注意 **shell 通配符不会自动展开**，需要先用 `glob.glob()` 展开：

```python
import glob
import json
import subprocess

# 批量评分，输出 CSV
skill_dirs = sorted(glob.glob("skills/*/"))
subprocess.run(
    ["python", "skill-metric/scripts/skill_quality_eval.py"]
    + skill_dirs
    + ["--csv", "skill_scores.csv"],
    check=True,
)

# 单个 skill，解析 JSON 结果
result = subprocess.run(
    ["python", "skill-metric/scripts/skill_quality_eval.py",
     "skills/uniprot-database", "-j"],
    capture_output=True, text=True, check=True,
)
data = json.loads(result.stdout)
print(data["total_score"])
```

更多 Python 调用示例和输出字段定义可参考 `skill-metric/references/scoring_criteria.md`。

---

## 注意事项与排错

- **路径必须是 skill 目录或 SKILL.md**：传入 `skills/` 这类父目录会被当作一个名为 `skills` 的 skill，通常不符合预期。
- **CSV 中的 `skill_dir`** 是**相对当前工作目录**的路径，注意在不同工作目录下运行会影响该字段。
- 同时使用 `--csv` 和 `-j` 时，**只会输出 CSV，不会输出 JSON**。
- `--figure` 仅支持单个 skill 且需要 `matplotlib`，否则会报错或被忽略。
