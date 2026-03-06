# Skill Metric — Scoring Criteria & Reference

Full details on the 24-point scoring rubric, output formats, and how to call the evaluation script from Python.

## Scoring Rubric (24 pts max)

### 2.1.1 Format (8 pts)

One point deducted per violation:

| Check | Pass condition |
|-------|---------------|
| SKILL.md exists and named `SKILL.md` | File present with exact name |
| Skill dir name format | No spaces or underscores in directory name |
| No `README.md` in dir | README.md absent (SKILL.md is the canonical doc) |
| YAML frontmatter present | File starts with `---` delimited block |
| `name` matches dir name | `name:` field equals the directory name |
| `description` field present | Non-empty `description:` in frontmatter |
| `description` under 1024 chars | Description length ≤ 1024 characters |
| `description` has no XML tags | No `<tag>` patterns in description |

### 2.1.2 Completeness (8 pts)

One point awarded per item present:

| Check | Pass condition |
|-------|---------------|
| `license` field | Non-empty `license:` in frontmatter |
| `compatibility` field (≤500 chars) | Non-empty `compatibility:` ≤ 500 chars |
| `metadata` field | `metadata:` block with at least one sub-key |
| `scripts/` subdir | Directory `scripts/` exists with ≥1 file |
| `references/` subdir | Directory `references/` exists with ≥1 file |
| `assets/` subdir | Directory `assets/` exists with ≥1 file |
| Body has concrete examples | Body contains at least one fenced code block |
| Body has error handling | Body describes errors/exceptions and how to handle them (retry, catch, troubleshoot) |

### 2.1.3 Writing (8 pts)

One point awarded per item:

| Check | Pass condition |
|-------|---------------|
| Description has clear task boundary | Description states what the skill does and does NOT do |
| Description has clear trigger | Description includes a use-case or trigger phrase |
| Progressive disclosure | SKILL.md body ≤ 5000 chars; details in `references/`, code in `scripts/` |
| Content primarily in English | ≥70% ASCII characters in a sample of body text |
| Refs consistent with dirs | Every `references/X` or `scripts/X` path mentioned in body has a matching file in the directory |
| Reverse consistency | `references/` or `scripts/` dirs present and body references at least one file |
| License not placeholder | `license:` value is not `"Unknown"`, `"TBD"`, or similar placeholder |
| Version info | Frontmatter or body contains version information |

---

## Output Formats

### Default (text report)

Human-readable per-skill report printed to stdout. Shows scores and per-check ✓/✗ with message.

### JSON (`-j`)

Single object (one skill) or array (multiple skills). Fields:

```json
{
  "skill_name": "biopython",
  "skill_dir": "skills/biopython",
  "format_score": 8,
  "completeness_score": 5,
  "writing_score": 6,
  "total_score": 19,
  "details": {
    "format": [{"pass": true, "message": "..."}],
    "completeness": [{"pass": false, "message": "..."}],
    "writing": [{"pass": true, "message": "..."}]
  }
}
```

### CSV (`--csv`)

One row per skill. Columns: `skill_name`, `skill_dir`, `format_score`, `completeness_score`, `writing_score`, `total_score`, `error`, then `format_1`…`format_8`, `completeness_1`…`completeness_8`, `writing_1`…`writing_8`, each cell containing `PASS: <message>` or `FAIL: <message>`.

### Radar chart (`--figure`)

PNG with three axes (Format, Completeness, Writing), scale 0–8. Title shows skill name and total score. Single-skill only; requires `matplotlib`.

---

## Calling from Python Code

**CRITICAL**: Shell glob patterns like `skills/*/` are expanded by the shell in a terminal. When calling from Python `subprocess` with a **list** argument, globs are NOT expanded — you must use `glob.glob()` first.

```python
import glob
import subprocess

# Expand skill directories in Python before passing to subprocess
skill_dirs = sorted(glob.glob('/path/to/skills/*/'))

# Score all skills and save CSV
subprocess.run(
    ['python', 'skills/skill-metric/scripts/skill_quality_eval.py']
    + skill_dirs
    + ['--csv', '/path/to/output/scores.csv'],
    check=True
)

# Score a single skill and parse JSON output
result = subprocess.run(
    ['python', 'skills/skill-metric/scripts/skill_quality_eval.py',
     '/path/to/skills/biopython', '-j'],
    capture_output=True, text=True, check=True
)
import json
data = json.loads(result.stdout)
print(data['total_score'])
```

---

## Notes

- Passing only `skills/` (the parent dir) is treated as one skill named "skills" — pass `skills/*/` or individual subdirs instead.
- CSV `skill_dir` values are **relative to current working directory**.
- If both `--csv` and `-j` are given, only CSV is produced.
- `--figure` is only supported for a single skill at a time.
