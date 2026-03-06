#!/usr/bin/env python3
"""
Skill static quality metrics evaluation script.

Scores a given skill directory against:
- 2.1.1 Format review (max 8 pts; -1 per violation)
- 2.1.2 Content completeness (base 0; +1 per satisfied item, max 8)
- 2.1.3 Writing quality (base 0; +1 per satisfied item, max 8)

Usage:
  python skill_quality_eval.py <skill_path>
  python skill_quality_eval.py /path/to/skill-name
  python skill_quality_eval.py /path/to/skill-name/SKILL.md
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from pathlib import Path


# --- YAML frontmatter parsing (no external deps) ---

def _parse_yaml_value(line: str) -> str | None:
    """Parse a single 'key: value' line; value may be quoted."""
    m = re.match(r"^\s*([a-zA-Z0-9_-]+)\s*:\s*(.*)$", line)
    if not m:
        return None
    raw = m.group(2).strip()
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("''", "'")
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace('\\"', '"')
    return raw if raw else None


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Split content into YAML frontmatter (between first --- and second ---) and body.
    Returns (parsed_dict, body_text). Parsed dict has top-level keys only;
    for nested (e.g. metadata) we only check presence.
    """
    parts = text.split("\n")
    if not parts or parts[0].strip() != "---":
        return {}, text

    yaml_lines: list[str] = []
    i = 1
    while i < len(parts):
        if parts[i].strip() == "---":
            i += 1
            break
        yaml_lines.append(parts[i])
        i += 1
    body = "\n".join(parts[i:]) if i < len(parts) else ""

    result: dict = {}
    for line in yaml_lines:
        if ":" in line and not line.strip().startswith("#"):
            key_m = re.match(r"^\s*([a-zA-Z0-9_-]+)\s*:\s*", line)
            if key_m:
                key = key_m.group(1)
                val = _parse_yaml_value(line)
                if key not in result:
                    result[key] = val
                elif isinstance(result[key], list):
                    result[key].append(val)
                else:
                    result[key] = [result[key], val]

    return result, body


def get_frontmatter_raw_yaml(text: str) -> str:
    """Get the raw YAML block (between first --- and second ---) for length checks."""
    parts = text.split("\n")
    if not parts or parts[0].strip() != "---":
        return ""
    yaml_lines: list[str] = []
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            break
        yaml_lines.append(parts[i])
    return "\n".join(yaml_lines)


# --- 2.1.1 Format review ---

def check_skill_file_exists(skill_dir: Path) -> tuple[bool, str]:
    """[skill_name]/SKILL.md must exist and be named exactly SKILL.md (not skill.md / SKILL.MD)."""
    p = skill_dir / "SKILL.md"
    if not p.exists():
        return False, f"SKILL.md missing (dir: {skill_dir})"
    if p.name != "SKILL.md":
        return False, "Filename must be exactly SKILL.md (case-sensitive)"
    return True, "Pass"


def check_skill_name_format(skill_name: str) -> tuple[bool, str]:
    """[skill_name] must have no spaces or underscores; use hyphen between words (e.g. notion-project-setup)."""
    if " " in skill_name:
        return False, "Skill dir name must not contain spaces"
    if "_" in skill_name:
        return False, "Skill dir name must not contain underscores; use hyphens (e.g. notion-project-setup)"
    if skill_name != skill_name.lower():
        return False, "Skill dir name should be lowercase with hyphens (e.g. notion-project-setup), not CamelCase"
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", skill_name):
        return False, "Skill dir name should only use lowercase letters, digits, and hyphens (e.g. my-skill-name)"
    return True, "Pass"


def check_no_readme(skill_dir: Path) -> tuple[bool, str]:
    """[skill_name]/ must not contain README.md."""
    readme = skill_dir / "README.md"
    if readme.exists():
        return False, "Dir must not contain README.md"
    return True, "Pass"


def check_has_frontmatter(content: str) -> tuple[bool, str]:
    """SKILL.md must have YAML frontmatter delimited by ---."""
    parts = content.strip().split("\n")
    if len(parts) < 2:
        return False, "File too short; missing YAML frontmatter"
    if parts[0].strip() != "---":
        return False, "YAML frontmatter must start with ---"
    found_second = False
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            found_second = True
            break
    if not found_second:
        return False, "YAML frontmatter must end with a second ---"
    return True, "Pass"


def check_name_field(fm: dict, skill_name: str) -> tuple[bool, str]:
    """Frontmatter must include name and it must match [skill_name] exactly."""
    name = fm.get("name")
    if name is None or (isinstance(name, str) and not name.strip()):
        return False, "YAML frontmatter missing name field"
    if isinstance(name, list):
        name = name[0] if name else ""
    if str(name).strip() != skill_name:
        return False, f"name must match dir name: expected '{skill_name}', got '{name}'"
    return True, "Pass"


def check_description_field(fm: dict) -> tuple[bool, str]:
    """Frontmatter must have description (what and when)."""
    desc = fm.get("description")
    if desc is None or (isinstance(desc, str) and not desc.strip()):
        return False, "YAML frontmatter missing description field"
    if isinstance(desc, list):
        desc = desc[0] if desc else ""
    return True, "Pass"


def check_description_length(desc: str) -> tuple[bool, str]:
    """description must be under 1024 characters."""
    if len(desc) >= 1024:
        return False, f"description must be under 1024 characters (got {len(desc)})"
    return True, "Pass"


def check_description_no_xml(desc: str) -> tuple[bool, str]:
    """description must not contain XML tags (e.g. <a>)."""
    if re.search(r"<[a-zA-Z][^>]*>", desc):
        return False, "description must not contain XML tags (e.g. <a>)"
    return True, "Pass"


# --- 2.1.2 Content completeness ---

def has_license(fm: dict) -> tuple[bool, str]:
    if fm.get("license") not in (None, ""):
        return True, "Has license field"
    return False, "No license field"


def has_compatibility(fm: dict) -> tuple[bool, str]:
    comp = fm.get("compatibility")
    if comp is None or (isinstance(comp, str) and not comp.strip()):
        return False, "No compatibility field"
    if isinstance(comp, str) and len(comp) > 500:
        return False, f"compatibility over 500 chars ({len(comp)})"
    return True, "Has compatibility field (≤500 chars)"


def has_metadata(fm: dict, raw_yaml: str) -> tuple[bool, str]:
    """Whether frontmatter or raw_yaml contains metadata with at least one sub-key (author, version, etc.)."""
    meta = fm.get("metadata")
    if meta is not None:
        if isinstance(meta, dict) and len(meta) > 0:
            return True, "Has metadata field (author, version, etc.)"
        if isinstance(meta, str) and meta.strip():
            return True, "Has metadata field (author, version, etc.)"
    # Check raw YAML for "metadata:" at line start followed by at least one indented sub-key
    if re.search(r"(?m)^\s*metadata\s*:\s*\n\s+[a-zA-Z0-9_-]+\s*:", raw_yaml):
        return True, "Has metadata field (author, version, etc.)"
    return False, "No metadata field or metadata block is empty (add e.g. author, version)"


def has_scripts_dir(skill_dir: Path) -> tuple[bool, str]:
    subdir = skill_dir / "scripts"
    if not subdir.is_dir():
        return False, "No scripts/ subdir"
    files = [p for p in subdir.iterdir() if p.is_file()]
    if files:
        return True, "Has scripts/ with at least one file"
    return False, "scripts/ exists but has no files"


def has_references_dir(skill_dir: Path) -> tuple[bool, str]:
    subdir = skill_dir / "references"
    if not subdir.is_dir():
        return False, "No references/ subdir"
    files = [p for p in subdir.iterdir() if p.is_file()]
    if files:
        return True, "Has references/ with at least one file"
    return False, "references/ exists but has no files"


def has_assets_dir(skill_dir: Path) -> tuple[bool, str]:
    subdir = skill_dir / "assets"
    if not subdir.is_dir():
        return False, "No assets/ subdir"
    files = [p for p in subdir.iterdir() if p.is_file()]
    if files:
        return True, "Has assets/ with at least one file"
    return False, "assets/ exists but has no files"


def has_examples_in_body(body: str) -> tuple[bool, str]:
    """Whether SKILL.md body provides concrete examples (non-trivial code block or substantive example text)."""
    code_blocks = re.findall(r"```[\s\S]*?```", body)
    total_lines = sum(block.count("\n") for block in code_blocks)
    total_inner = sum(len(block.strip().strip("`").strip()) for block in code_blocks)
    if code_blocks and (total_lines >= 3 or total_inner >= 20):
        return True, "Body contains concrete examples (code block)"
    lower = body.lower()
    example_keywords = ("example", "示例", "案例", "e.g.", "for example")
    if any(kw in lower or kw in body for kw in example_keywords):
        # Require some surrounding context: paragraph or section with example has min length
        for kw in ["example", "示例", "案例", "e.g.", "for example"]:
            idx = body.find(kw) if kw in ("示例", "案例") else lower.find(kw)
            if idx == -1:
                continue
            start = max(0, idx - 80)
            end = min(len(body), idx + 80)
            snippet = body[start:end]
            if len(snippet.strip()) >= 30:
                return True, "Body contains examples"
    return False, "No clear examples: need at least one non-trivial code block or example paragraph"


def has_error_handling_in_body(body: str) -> tuple[bool, str]:
    """Whether SKILL.md describes both errors/exceptions and how to handle them."""
    lower = body.lower()
    error_words = ("error", "exception", "错误", "异常", "troubleshoot", "failure")
    handling_words = ("retry", "catch", "handle", "fallback", "重试", "处理", "解决", "troubleshooting")
    has_error = any(w in lower or w in body for w in error_words)
    has_handling = any(w in lower or w in body for w in handling_words)
    if has_error and has_handling:
        return True, "Body describes error/exception handling"
    if re.search(r"^#+\s*.*(?:troubleshoot|error|exception|错误|异常)", body, re.MULTILINE | re.IGNORECASE):
        return True, "Body has error-handling / troubleshooting section"
    return False, "Body should describe both errors/exceptions and how to handle them (e.g. retry, catch, troubleshooting)"


# --- 2.1.3 Writing quality ---

def description_has_task_boundary(desc: str) -> tuple[bool, str]:
    """Whether description has a clear task boundary (what it does)."""
    if len(desc) < 40:
        return False, "description too short to determine task boundary (e.g. at least 40 chars)"
    vague = re.search(r"\b(helps? with|assists? with|supports? .{0,20}\.)", desc.lower())
    if vague and len(desc) < 80:
        return False, "description too vague (e.g. helps with); needs concrete task description"
    return True, "description has clear task boundary"


def description_has_trigger(desc: str) -> tuple[bool, str]:
    """Whether description has a clear trigger (e.g. Use when) and is long enough to be substantive."""
    lower = desc.lower()
    trigger_phrases = ("use when", "when to use", "use for", "when the user", "when you", "trigger")
    if any(phrase in lower for phrase in trigger_phrases) and len(desc.strip()) >= 30:
        return True, "description includes use case/trigger"
    return False, "no clear trigger in description or too short (consider adding e.g. Use when...)"


def progressive_disclosure(skill_dir: Path, body: str, skill_name: str) -> tuple[bool, str]:
    """SKILL.md core under 5k chars; details in references/, code in scripts/."""
    body_len = len(body)
    under_5k = body_len < 5000
    has_ref = (skill_dir / "references").is_dir()
    has_scripts = (skill_dir / "scripts").is_dir()
    if under_5k and (has_ref or has_scripts):
        return True, f"SKILL.md body {body_len} chars with references/ or scripts/ (progressive disclosure)"
    if under_5k:
        return True, f"SKILL.md body {body_len} chars (<5k); consider moving details to references/, code to scripts/"
    return False, f"SKILL.md body {body_len} chars (over 5k); move details to references/, code to scripts/"


def primarily_english(skill_dir: Path, content: str) -> tuple[bool, str]:
    """Whether main content is primarily in English (sample: frontmatter + first 2000 chars)."""
    sample = content[: 2000]
    non_ascii = sum(1 for c in sample if ord(c) > 127)
    total = len(sample)
    if total == 0:
        return True, "No content to check"
    ratio = 1 - (non_ascii / total)
    if ratio >= 0.85:
        return True, f"~{ratio*100:.0f}% ASCII in sample; primarily English"
    return False, f"sample has notable non-ASCII (~{(1-ratio)*100:.0f}%); suggest English for main content"


def _extract_refs_to_refs_or_scripts(body: str) -> list[tuple[str, str]]:
    """Extract references to references/ or scripts/ from body; return [(dir_type, name)]."""
    # Match references/ or scripts/ (optional leading / or `), then filename; support .txt, .csv and common exts
    pattern = r"[/`]?(references|scripts)/([a-zA-Z0-9_.-]+?)(?:\.(?:md|py|sh|json|yaml|yml|txt|csv))?(?:\s|/|\)|\]|`|$)"
    found = set()
    for m in re.finditer(pattern, body):
        dir_type = m.group(1)
        name = m.group(2).strip()
        if not name or (dir_type, name) in found:
            continue
        found.add((dir_type, name))
    return list(found)


def references_and_scripts_refs_consistent(skill_dir: Path, body: str) -> tuple[bool, str]:
    """Refs and dirs consistent: every references/ or scripts/ ref in body points to an existing file."""
    refs = _extract_refs_to_refs_or_scripts(body)
    if not refs:
        return True, "Body does not reference references/ or scripts/; nothing to check"
    missing = []
    for dir_type, name in refs:
        subdir = skill_dir / dir_type
        if not subdir.is_dir():
            missing.append(f"{dir_type}/ dir missing")
            continue
        # Resolve name to any file: name, name.ext, or name*
        candidates = list(subdir.glob(f"{re.escape(name)}*"))
        if not any(p.is_file() for p in candidates):
            missing.append(f"{dir_type}/{name} (no file matching {name} or {name}.*) not found")
    if missing:
        return False, "Refs and dirs inconsistent: " + "; ".join(missing)
    return True, "All references/ and scripts/ refs in body point to existing files"


def refs_or_scripts_referenced_in_body(skill_dir: Path, body: str) -> tuple[bool, str]:
    """Reverse consistency: if references/ or scripts/ exist and are non-empty, body references at least one file."""
    refs_dir = skill_dir / "references"
    scripts_dir = skill_dir / "scripts"
    if not refs_dir.is_dir() and not scripts_dir.is_dir():
        return True, "No references/ or scripts/ dirs; nothing to check"
    refs = _extract_refs_to_refs_or_scripts(body)
    ref_names = {name for d, name in refs if d == "references"}
    script_names = {name for d, name in refs if d == "scripts"}
    if refs_dir.is_dir():
        existing_refs = {p.stem for p in refs_dir.iterdir() if p.is_file()}
        if existing_refs and not ref_names:
            return False, "references/ has files but body does not reference any file in it"
    if scripts_dir.is_dir():
        existing_scripts = {p.stem for p in scripts_dir.iterdir() if p.is_file()}
        if existing_scripts and not script_names:
            return False, "scripts/ has files but body does not reference any file in it"
    return True, "references/ or scripts/ present and body references at least one file (or dirs empty)"


def license_not_placeholder(fm: dict) -> tuple[bool, str]:
    """Whether license is a non-placeholder value (exclude Unknown, empty, N/A, etc.)."""
    raw = fm.get("license")
    if raw is None:
        return False, "No license field"
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    s = (raw or "").strip()
    if not s:
        return False, "license is empty"
    lower = s.lower()
    placeholders = {"unknown", "n/a", "na", "none", "null", "tbd", "todo", "-", "待定", "未定"}
    if lower in placeholders:
        return False, "license is a placeholder (e.g. Unknown/N/A)"
    return True, "license is a non-placeholder value"


def has_version_info(fm: dict, raw_yaml: str, body: str) -> tuple[bool, str]:
    """Whether frontmatter or body contains library/data version; prefer frontmatter / Version section, stricter body regex."""
    for key in ("version", "skill-version", "data-version", "idc-data-version"):
        val = fm.get(key)
        if val is not None and str(val).strip():
            return True, "Frontmatter contains version info"
    if re.search(r"^\s*(?:version|skill-version|data-version)\s*:", raw_yaml, re.MULTILINE | re.IGNORECASE):
        return True, "Frontmatter contains version info"
    # Prefer non-code body: strip code blocks then search in first 2000 chars
    body_no_fences = re.sub(r"```[\s\S]*?```", "", body[: 4000])
    sample = body_no_fences[: 2000]
    # Prefer version in a fixed section (## Version / 版本)
    version_section = re.search(
        r"^#+\s*.*(?:version|版本|data\s+version)\s*$.*?(?=^#+|\Z)",
        body_no_fences,
        re.MULTILINE | re.IGNORECASE | re.DOTALL,
    )
    if version_section:
        section_text = version_section.group(0)[: 500]
        if re.search(r"\b(?:version|v)\s*[:\s]*\d+(?:\.\d+)*", section_text, re.IGNORECASE):
            return True, "Body contains version info (Version section)"
        if re.search(r"(?:^|\s)(v\d+(?:\.\d+)*)(?:\s|[,.)]|$)", section_text):
            return True, "Body contains version info (Version section)"
    # Stricter regex in body: avoid string literals and variable names like v1 = 2
    if re.search(r"\b(?:version|v)\s*[:\s]+\d+(?:\.\d+)*", sample, re.IGNORECASE):
        return True, "Body contains version info"
    if re.search(r"(?:^|\s)(v\d+(?:\.\d+)*)(?:\s|[,.)]|$)", sample):
        return True, "Body contains version info"
    if re.search(r"\d+\.\d+(?:\.\d+)*\s*(?:\(released|as of|current)", sample, re.IGNORECASE):
        return True, "Body contains version info"
    return False, "No library/data version info in frontmatter or Version section"


# --- Main runner ---

def resolve_skill_path(path: str) -> tuple[Path, str]:
    """Resolve input to (skill_dir, skill_name)."""
    p = Path(path).resolve()
    if p.is_file() and p.name.upper() == "SKILL.MD":
        skill_dir = p.parent
    elif p.is_dir():
        skill_dir = p
    else:
        raise FileNotFoundError(f"Path not found or not SKILL.md / dir: {path}")
    skill_name = skill_dir.name
    return skill_dir, skill_name


def evaluate_skill(skill_path: str) -> dict:
    """Evaluate a single skill against all metrics; return structured result."""
    skill_dir, skill_name = resolve_skill_path(skill_path)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {
            "skill_name": skill_name,
            "skill_dir": str(skill_dir),
            "error": "SKILL.md not found",
            "format_score": 0,
            "completeness_score": 0,
            "writing_score": 0,
            "total_score": 0,
            "details": {},
        }

    content = skill_md.read_text(encoding="utf-8", errors="replace")
    fm, body = parse_frontmatter(content)
    raw_yaml = get_frontmatter_raw_yaml(content)
    desc = fm.get("description") or ""
    if isinstance(desc, list):
        desc = desc[0] or ""

    details: dict = {}
    format_score = 8
    completeness_score = 0
    writing_score = 0

    # 2.1.1 Format review (max 8; -1 per violation)
    format_checks = [
        ("SKILL.md exists and named SKILL.md", check_skill_file_exists(skill_dir)),
        ("skill dir name format (no spaces/underscores)", check_skill_name_format(skill_name)),
        ("No README.md in dir", check_no_readme(skill_dir)),
        ("YAML frontmatter present (--- delimited)", check_has_frontmatter(content)),
        ("name matches dir name", check_name_field(fm, skill_name)),
        ("description field present", check_description_field(fm)),
        ("description under 1024 chars", check_description_length(desc)),
        ("description has no XML tags", check_description_no_xml(desc)),
    ]
    details["format"] = []
    for label, (ok, msg) in format_checks:
        if not ok:
            format_score -= 1
            details["format"].append({"item": label, "pass": False, "message": msg})
        else:
            details["format"].append({"item": label, "pass": True, "message": msg})

    # 2.1.2 Content completeness (+1 per item, max 8)
    comp_checks = [
        has_license(fm),
        has_compatibility(fm),
        has_metadata(fm, raw_yaml),
        has_scripts_dir(skill_dir),
        has_references_dir(skill_dir),
        has_assets_dir(skill_dir),
        has_examples_in_body(body),
        has_error_handling_in_body(body),
    ]
    comp_labels = [
        "license field",
        "compatibility field (≤500 chars)",
        "metadata field",
        "scripts/ subdir",
        "references/ subdir",
        "assets/ subdir",
        "body has concrete examples",
        "body has error handling",
    ]
    details["completeness"] = []
    for label, (ok, msg) in zip(comp_labels, comp_checks):
        if ok:
            completeness_score += 1
            details["completeness"].append({"item": label, "pass": True, "message": msg})
        else:
            details["completeness"].append({"item": label, "pass": False, "message": msg})

    # 2.1.3 Writing quality (+1 per item, 8 items, max 8)
    writing_checks = [
        ("description has clear task boundary", description_has_task_boundary(desc)),
        ("description has clear trigger", description_has_trigger(desc)),
        ("progressive disclosure", progressive_disclosure(skill_dir, body, skill_name)),
        ("content primarily in English", primarily_english(skill_dir, content)),
        ("refs consistent with dirs", references_and_scripts_refs_consistent(skill_dir, body)),
        ("reverse consistency (refs/scripts referenced)", refs_or_scripts_referenced_in_body(skill_dir, body)),
        ("license not placeholder", license_not_placeholder(fm)),
        ("version info (frontmatter or body)", has_version_info(fm, raw_yaml, body)),
    ]
    details["writing"] = []
    for label, (ok, msg) in writing_checks:
        if ok:
            writing_score += 1
            details["writing"].append({"item": label, "pass": True, "message": msg})
        else:
            details["writing"].append({"item": label, "pass": False, "message": msg})

    total = format_score + completeness_score + writing_score
    return {
        "skill_name": skill_name,
        "skill_dir": str(skill_dir),
        "error": None,
        "format_score": format_score,
        "completeness_score": completeness_score,
        "writing_score": writing_score,
        "total_score": total,
        "details": details,
    }


def results_to_csv(all_results: list[dict]) -> tuple[list[str], list[list[str]]]:
    """Build CSV header and rows from evaluate_skill() results. Each row = one skill; columns = scores + PASS/FAIL and message per check."""
    header = [
        "skill_name",
        "skill_dir",
        "format_score",
        "completeness_score",
        "writing_score",
        "total_score",
        "error",
    ]
    for skey in ("format", "completeness", "writing"):
        for i in range(1, 9):
            header.append(f"{skey}_{i}")

    rows = []
    cwd = Path.cwd()
    for r in all_results:
        skill_name = r.get("skill_name") or (Path(r.get("skill_path", "")).name if r.get("skill_path") else "")
        skill_dir = r.get("skill_dir", "")
        try:
            if skill_dir:
                skill_dir = str(Path(skill_dir).relative_to(cwd))
        except (ValueError, TypeError):
            pass
        row = [
            str(skill_name),
            str(skill_dir),
            r.get("format_score", ""),
            r.get("completeness_score", ""),
            r.get("writing_score", ""),
            r.get("total_score", ""),
            r.get("error", ""),
        ]
        details = r.get("details") or {}
        for skey in ("format", "completeness", "writing"):
            for d in details.get(skey, []):
                status = "PASS" if d.get("pass") else "FAIL"
                msg = d.get("message", "")
                row.append(f"{status}: {msg}" if msg else status)
        while len(row) < len(header):
            row.append("")
        rows.append(row[: len(header)])
    return header, rows


def format_report(result: dict, verbose: bool = True) -> str:
    """Build a human-readable score report."""
    lines = [
        "",
        "=" * 60,
        f"Skill quality score: {result['skill_name']}",
        f"Path: {result['skill_dir']}",
        "=" * 60,
        "",
        f"  2.1.1 Format:        {result['format_score']}/8",
        f"  2.1.2 Completeness:  {result['completeness_score']}/8",
        f"  2.1.3 Writing:       {result['writing_score']}/8",
        "",
        f"  Total:               {result['total_score']}/24",
        "",
    ]
    if result.get("error"):
        lines.append(f"  Error: {result['error']}\n")
        return "\n".join(lines)

    if verbose and result.get("details"):
        for section, key in [("Format", "format"), ("Completeness", "completeness"), ("Writing", "writing")]:
            lines.append(f"--- {section} ---")
            for d in result["details"][key]:
                status = "✓" if d["pass"] else "✗"
                lines.append(f"  [{status}] {d['item']}: {d['message']}")
            lines.append("")
    return "\n".join(lines)


def plot_radar(result: dict, output_path: str | Path) -> None:
    """Plot a radar chart for a single skill's format/completeness/writing scores. Requires matplotlib."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        raise SystemExit("--figure requires matplotlib. Install with: pip install matplotlib") from None

    skill_name = result.get("skill_name", "skill")
    format_s = result.get("format_score", 0) or 0
    comp_s = result.get("completeness_score", 0) or 0
    writing_s = result.get("writing_score", 0) or 0
    total = result.get("total_score", 0) or 0

    labels = ["Format\n(2.1.1)", "Completeness\n(2.1.2)", "Writing\n(2.1.3)"]
    values = [format_s, comp_s, writing_s]
    # Angles for 3 axes + close the loop (same as test.py)
    angles = np.linspace(0, 2 * np.pi, 3, endpoint=False).tolist()
    angles += angles[:1]
    values_closed = list(values) + [values[0]]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    # First axis at top, clockwise (same as test.py)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 8)
    ax.set_yticks([2, 4, 6, 8])
    ax.set_yticklabels(["2", "4", "6", "8"])
    ax.plot(angles, values_closed, "o-", linewidth=2, label="Score")
    ax.fill(angles, values_closed, alpha=0.25)
    ax.set_title(f"{skill_name}\nTotal: {total}/24", pad=20)
    fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.08)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", pad_inches=0.3)
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score skills by static quality metrics (format 8 + completeness 8 + writing 8 = 24 max)"
    )
    parser.add_argument(
        "skill_path",
        nargs="+",
        help="Skill dir path(s) or SKILL.md path(s)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only print total scores",
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Output JSON",
    )
    parser.add_argument(
        "--csv",
        nargs="?",
        default=None,
        const="",
        metavar="OUTPUT.csv",
        help="Output results as CSV (to file if path given, else stdout). One row per skill with scores and per-check remarks.",
    )
    parser.add_argument(
        "--figure",
        nargs="?",
        default=None,
        const="",
        metavar="OUTPUT.png",
        help="Generate a radar chart (only when evaluating a single skill). Output path optional; default: <skill_name>_radar.png",
    )
    args = parser.parse_args()

    import json as _json

    all_results = []
    for path in args.skill_path:
        try:
            result = evaluate_skill(path)
            all_results.append(result)
            if args.json or args.csv is not None:
                continue
            print(format_report(result, verbose=not args.quiet))
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            all_results.append({
                "skill_path": path,
                "error": str(e),
                "total_score": None,
            })
        except Exception as e:
            print(f"Error processing {path}: {e}", file=sys.stderr)
            all_results.append({"skill_path": path, "error": str(e), "total_score": None})

    if args.csv is not None:
        header, rows = results_to_csv(all_results)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(header)
        writer.writerows(rows)
        csv_text = buf.getvalue()
        if args.csv:
            Path(args.csv).write_text(csv_text, encoding="utf-8")
        else:
            print(csv_text, end="")
    elif args.json:
        print(_json.dumps(all_results if len(all_results) != 1 else all_results[0], ensure_ascii=False, indent=2))

    if args.figure is not None and len(all_results) == 1:
        r = all_results[0]
        if r.get("error") or r.get("total_score") is None:
            print("Cannot generate radar chart: skill evaluation had an error.", file=sys.stderr)
        else:
            out = args.figure if args.figure else f"{r.get('skill_name', 'skill')}_radar.png"
            try:
                plot_radar(r, out)
                print(f"Radar chart saved: {out}", file=sys.stderr)
            except Exception as e:
                print(f"Failed to save radar chart: {e}", file=sys.stderr)
                return 1
    elif args.figure is not None and len(all_results) != 1:
        print("--figure is only supported when evaluating a single skill.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
