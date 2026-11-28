# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate and validate the three Material Workflow Wiki indexes."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "docs/wiki"
LEVELS = {"source": "来源已核", "single": "单件复现", "independent": "独立复验"}
STAGES = {"bake": "01 · 烘焙", "mask": "02 · 图层和遮罩", "weathering": "03 · 做旧", "export": "04 · 导出"}
FIELDS = {"id", "title", "stage", "material", "effect", "channel", "symptom", "evidence", "applies"}
LINK = re.compile(r'!?\[[^\]\n]+\]\(([^\s)]+)\)')
META = re.compile(r'^# [^\n]+\n\n<!-- wiki-index: (\{[^\n]+\}) -->\n')
SECTIONS = ("任务", "输入", "执行", "通过条件", "失败处理", "证据")


def entries(wiki):
    result, ids = [], set()
    for p in sorted((wiki / "techniques").glob("*.md")):
        s = p.read_text(encoding="utf-8")
        match = META.match(s)
        if not match:
            raise ValueError(f"{p.name}: missing wiki-index metadata")
        row = json.loads(match[1])
        if set(row) != FIELDS or any(not isinstance(v, str) or not v.strip() for v in row.values()):
            raise ValueError(f"{p.name}: invalid metadata fields")
        if any(any(c in v for c in '\n\r[]|<>') for v in row.values()):
            raise ValueError(f"{p.name}: unsupported metadata characters")
        if not re.fullmatch(r"MW-[0-9]{3}", row["id"]) or row["id"] in ids:
            raise ValueError(f"{p.name}: invalid or duplicate technique ID")
        if row["stage"] not in STAGES or row["evidence"] not in LEVELS:
            raise ValueError(f"{p.name}: unknown stage or evidence level")
        if s.splitlines()[0] != "# " + row["title"]:
            raise ValueError(f"{p.name}: title mismatch")
        if re.findall(r'^## (.+)$', s, re.M) != list(SECTIONS):
            raise ValueError(f"{p.name}: wrong section order")
        ids.add(row["id"])
        result.append((p, row))
    if not result:
        raise ValueError("No techniques")
    return result


def render(rows, title, group, sort_key=None):
    groups = {}
    for p, row in rows:
        groups.setdefault(group(row), []).append((p, row))
    lines = [f"# {title}", "", "自动生成。编辑工艺页，不手改此页。", ""]
    for label in sorted(groups, key=sort_key):
        lines.extend([f"## {label}", ""])
        for p, row in sorted(groups[label], key=lambda pair: pair[1]["id"]):
            lines.append(f'- [{row["id"]} · {row["title"]}](../techniques/{p.name}) · {LEVELS[row["evidence"]]}')
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def check_links(wiki):
    errors = []
    for p in sorted(wiki.rglob("*.md")):
        for link in LINK.findall(p.read_text(encoding="utf-8")):
            u = urlsplit(link)
            if u.scheme in {"https", "http"} and u.netloc:
                continue
            if u.scheme or u.netloc:
                errors.append(f"{p.name}: unsupported link: {link}")
                continue
            q = (p.parent / unquote(u.path)).resolve() if u.path else p
            if not q.is_relative_to(wiki.resolve()) or not q.is_file():
                errors.append(f"{p.name}: broken local link: {link}")
    return errors


def run(wiki, write=False):
    rows = entries(wiki)
    generated = {
        "make-assets.md": render(rows, "做资产", lambda x: STAGES[x["stage"]]),
        "find-technique.md": render(rows, "查工艺", lambda x: f'{x["material"]} / {x["effect"]} / {x["channel"]}'),
        "troubleshoot.md": render(rows, "排故", lambda x: x["symptom"]),
    }
    errors = []
    for name, data in generated.items():
        path = wiki / "indexes" / name
        if write:
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(data.encode("utf-8"))
        elif not path.is_file() or path.read_bytes() != data.encode("utf-8"):
            errors.append(f"stale index: {name}")
    errors.extend(check_links(wiki))
    if errors:
        raise ValueError("\n".join(errors))
    return len(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write", action="store_true", help="regenerate the indexes before validation")
    args = p.parse_args()
    try:
        print(f"Wiki check passed: {run(WIKI, args.write)} pages, 3 indexes")
    except (OSError, ValueError) as exc:
        p.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
