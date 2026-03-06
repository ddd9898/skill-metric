## Skill Metric — Static Quality Evaluation for Skills

`skills/skill-metric` is a utility skill that runs **static quality checks** on agent skills.  
It scores each target skill directory on three dimensions:

- **2.1.1 Format**
- **2.1.2 Completeness**
- **2.1.3 Writing**

Each dimension has a maximum of **8 points**, for a total of **24 points**, and the tool supports **text reports, JSON, CSV, and radar charts** (for a single skill).

The main implementation script lives at `skills/skill-metric/scripts/skill_quality_eval.py`.

---

## When to Use This Tool

- **Batch quality audit**: Run a health check on all skills under `skills/` to detect format or content issues.
- **Deep-dive on a single skill**: Get detailed Format / Completeness / Writing scores plus per-check explanations.
- **Export for analysis**: Export scores as **CSV** or **JSON** for dashboards, BI tools, or further processing.
- **Generate radar charts**: For a single skill, create a radar chart over the three dimensions for reports or slide decks.

---

## Dependencies

- **Python**: Python 3.10+ is recommended.
- **Third‑party libraries**:
  - Core scoring logic uses only the standard library.
  - Radar chart generation via `--figure` requires: `pip install matplotlib`.

---

## CLI Usage

Use the script under `skills/skill-metric/scripts/skill_quality_eval.py`:

```bash
python skills/skill-metric/scripts/skill_quality_eval.py <skill_path> [skill_path ...] [options]
```

### Positional arguments

| Argument | Description |
|----------|-------------|
| `skill_path` | One or more skill directory paths, or a path to the corresponding `SKILL.md`. Examples: `skills/uniprot-database` or `skills/uniprot-database/SKILL.md`. |

**Important**: Each path must be either a **skill directory** or its **`SKILL.md`** file. Passing the parent `skills/` directory itself will treat it as a single skill named `skills`, which is almost never what you want.

### Options

| Option | Description |
|--------|-------------|
| `-q`, `--quiet` | Print only the total score for each skill. |
| `-j`, `--json` | Print JSON output (single object for one skill, array for multiple). |
| `--csv` [file] | Emit CSV. Without a path, CSV is written to stdout; with a path, CSV is saved to that file. |
| `--figure` [file] | Generate a radar chart PNG for **one** skill only. Without a path, saves as `<skill_name>_radar.png`; with a path, saves to that file. Requires `matplotlib`. |

---

## Examples

```bash
# Score a single skill with a full verbose report
python skills/skill-metric/scripts/skill_quality_eval.py skills/uniprot-database

# Score a single skill and print only the total score
python skills/skill-metric/scripts/skill_quality_eval.py skills/uniprot-database -q

# Score a single skill and generate a radar chart (default <skill_name>_radar.png)
python skills/skill-metric/scripts/skill_quality_eval.py skills/uniprot-database --figure

# Score a single skill and save the radar chart to a custom file
python skills/skill-metric/scripts/skill_quality_eval.py skills/uniprot-database --figure report/radar.png

# Batch‑score all skills under skills/
python skills/skill-metric/scripts/skill_quality_eval.py skills/*/

# Batch‑score and write CSV to a file
python skills/skill-metric/scripts/skill_quality_eval.py skills/*/ --csv skill_scores.csv

# Batch‑score and emit CSV to stdout (can be redirected)
python skills/skill-metric/scripts/skill_quality_eval.py skills/*/ --csv > report.csv

# JSON output
python skills/skill-metric/scripts/skill_quality_eval.py skills/uniprot-database -j
python skills/skill-metric/scripts/skill_quality_eval.py skills/*/ -j
```

---

## Scoring Overview (24 Points Total)

For full details see `skills/skill-metric/references/scoring_criteria.md`.  
This section summarizes the rubric:

| Dimension | What is checked (summary) | Max |
|----------|---------------------------|-----|
| **2.1.1 Format** | `SKILL.md` existence and exact name, directory naming rules, YAML frontmatter, `name`/`description` presence and validity, description length and no XML tags; one point deducted per violation. | 8 |
| **2.1.2 Completeness** | Presence of `license`, `compatibility`, `metadata`; existence of non‑empty `scripts/`, `references/`, `assets/` dirs; code examples; error‑handling guidance; one point awarded per satisfied item. | 8 |
| **2.1.3 Writing** | Clear task boundary and trigger, progressive disclosure (body ≤ 5000 chars), English‑first content, consistency between body references and actual files, non‑placeholder license, version information, etc.; one point awarded per satisfied item. | 8 |

---

## Output Formats

### Text report (default)

- One section per skill, showing: skill name, path, Format / Completeness / Writing scores, and total score.
- Unless `-q` is used, each individual check is listed with ✓/✗ and an explanatory message, making it easy to see where the skill fails the rubric.

### JSON (`-j`)

- **Single skill**: A JSON object containing `skill_name`, `skill_dir`, `format_score`, `completeness_score`, `writing_score`, `total_score`, and a `details` object grouping per‑check results under `format`, `completeness`, and `writing`.
- **Multiple skills**: An array of such objects, convenient for downstream processing and visualization.

### CSV (`--csv`)

- **Columns**: `skill_name`, `skill_dir` (relative to the current working directory), `format_score`, `completeness_score`, `writing_score`, `total_score`, `error`, plus `format_1`…`format_8`, `completeness_1`…`completeness_8`, `writing_1`…`writing_8`.
- Each per‑check column contains `PASS: <message>` or `FAIL: <message>`.  
  This makes it easy to filter, aggregate, or pivot on particular checks in tools like Excel or data warehouses.

### Radar chart (`--figure`)

- Only generated when **exactly one skill** is evaluated and that skill completes without errors.
- The chart has three axes — Format (2.1.1), Completeness (2.1.2), Writing (2.1.3) — each on a 0–8 scale.  
  The title includes the skill name and total score.
- When multiple skills are passed together with `--figure`, the script prints a message indicating that radar charts are supported for single‑skill evaluation only.

---

## Calling from Python

When invoking the script from Python, remember that **shell glob patterns are not expanded** if you pass a list to `subprocess`. Use `glob.glob()` first:

```python
import glob
import json
import subprocess

# Batch‑score all skills and write CSV
skill_dirs = sorted(glob.glob("skills/*/"))
subprocess.run(
    ["python", "skills/skill-metric/scripts/skill_quality_eval.py"]
    + skill_dirs
    + ["--csv", "skill_scores.csv"],
    check=True,
)

# Score a single skill and parse JSON output
result = subprocess.run(
    ["python", "skills/skill-metric/scripts/skill_quality_eval.py",
     "skills/uniprot-database", "-j"],
    capture_output=True, text=True, check=True,
)
data = json.loads(result.stdout)
print(data["total_score"])
```

For more Python examples and a precise description of all fields, see `skills/skill-metric/references/scoring_criteria.md`.

---

## Notes and Troubleshooting

- **Valid paths only**: Each path must be a skill directory or its `SKILL.md`. Passing the parent `skills/` directory will treat it as a single skill called `skills`.
- **Relative `skill_dir` in CSV**: The `skill_dir` column in CSV is **relative to the current working directory**, so running the tool from different locations will change this value.
- **`--csv` vs `-j`**: If both `--csv` and `-j` are provided, only CSV is emitted (JSON is suppressed).
- **Radar chart requirements**: `--figure` is supported for one skill at a time and requires `matplotlib`; otherwise, the option may be ignored or an error message will be shown.

