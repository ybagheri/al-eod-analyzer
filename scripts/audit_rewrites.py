"""S2.8b R-FINISH audit: recover ad-hoc enum rewrite rules from git history.

Walks every artifacts/extraction_queue/*.response.json file through its full
commit history and records every day_type / event-label value change
(old -> new) with example image ids.

Outputs (both committed):
- artifacts/rewrite_history_audit.json : every observed rule with count + examples
- artifacts/lossy_normalizations.json  : same rules grouped by (category, from_id),
  classified ``exact`` when every observed target matches the v1 synonym table
  for that raw id, ``lossy`` otherwise (needs a user/ADR decision).

Read-only analysis; regenerates both artifacts deterministically.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
TAXONOMY = REPO / "config" / "taxonomy.yaml"
ARTIFACTS = REPO / "artifacts"
AUDIT_NAME = "rewrite_history_audit.json"
LOSSY_NAME = "lossy_normalizations.json"


def run(args: list[str]) -> str:
    proc = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO
    )
    if proc.returncode != 0:
        raise SystemExit(f"git failed: {args}\n{proc.stderr}")
    return proc.stdout


def _repo_blob(ref: str, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO,
    )
    return proc.stdout if proc.returncode == 0 else None


def _synonym_table() -> dict[tuple[str, str], set[str]]:
    """(category, normalized_raw) -> canonical ids the raw id may denote."""
    data = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    table: dict[tuple[str, str], set[str]] = defaultdict(set)
    for raw, target in (data.get("event_synonyms") or {}).items():
        table[("event", str(raw).strip().lower())].add(str(target))
    for raw, target in (data.get("day_type_synonyms") or {}).items():
        table[("day_type", str(raw).strip().lower())].add(str(target))
    return table


def collect_rules() -> tuple[list[dict[str, Any]], int, int]:
    paths = run(["git", "ls-tree", "-r", "--name-only", "HEAD"]).splitlines()
    queue = [
        p for p in paths if p.startswith("artifacts/extraction_queue/") and ".response.json" in p
    ]
    rules: Counter[tuple[str, str, str]] = Counter()
    examples: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    parse_fail = 0
    for path in queue:
        image_id = path.rsplit(".", 2)[0].rsplit("/", 1)[-1]
        revs = run(["git", "rev-list", "--all", "--", path]).splitlines()
        revs.reverse()
        prev: dict[str, Any] | None = None
        for rev in revs:
            blob = _repo_blob(rev, path)
            if blob is None:
                continue
            try:
                payload = json.loads(blob)
            except json.JSONDecodeError:
                parse_fail += 1
                continue
            if not isinstance(payload, dict):
                continue
            if prev is not None:
                old_dt, new_dt = prev.get("day_type"), payload.get("day_type")
                if isinstance(old_dt, str) and isinstance(new_dt, str) and old_dt != new_dt:
                    key = ("day_type", old_dt, new_dt)
                    rules[key] += 1
                    examples[key].add(image_id)
                for oe, ne in zip(
                    prev.get("events") or [], payload.get("events") or [], strict=False
                ):
                    if not isinstance(oe, dict) or not isinstance(ne, dict):
                        continue
                    ol, nl = oe.get("label"), ne.get("label")
                    if isinstance(ol, str) and isinstance(nl, str) and ol != nl:
                        key = ("event", ol, nl)
                        rules[key] += 1
                        examples[key].add(image_id)
                    if isinstance(ol, str) and nl is None:
                        key = ("event_null", ol, "<null>")
                        rules[key] += 1
                        examples[key].add(image_id)
            prev = payload
    out = [
        {
            "category": cat,
            "from": old,
            "to": new,
            "count": count,
            "examples": sorted(examples[(cat, old, new)])[:10],
        }
        for (cat, old, new), count in sorted(rules.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return out, parse_fail, len(queue)


def build_lossy_normalizations(rules: list[dict[str, Any]]) -> dict[str, Any]:
    table = _synonym_table()
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for rule in rules:
        key = (str(rule["category"]), str(rule["from"]))
        group = groups.setdefault(
            key, {"category": key[0], "from": key[1], "targets": {}, "total": 0}
        )
        targets: dict[str, int] = group["targets"]
        to = str(rule["to"])
        targets[to] = targets.get(to, 0) + int(rule["count"])
        group["total"] += int(rule["count"])
    out = []
    for (category, from_id), group in sorted(groups.items()):
        targets: dict[str, int] = group["targets"]
        table_cat = "event" if category == "event_null" else category
        allowed = table.get((table_cat, from_id.replace("_", " ").lower()), set())
        exact = bool(targets) and all(to in allowed for to in targets)
        entry: dict[str, Any] = {
            "category": category,
            "from": from_id,
            "total": group["total"],
            "targets": targets,
            "quality": "exact" if exact else "lossy",
        }
        if not exact:
            entry["note"] = "review group: target must come from chart context or a new ADR"
        out.append(entry)
    return {"schema_version": 1, "rules": out}


def main() -> None:
    rules, parse_fail, files = collect_rules()
    (ARTIFACTS / AUDIT_NAME).write_text(
        json.dumps({"rules": rules}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (ARTIFACTS / LOSSY_NAME).write_text(
        json.dumps(build_lossy_normalizations(rules), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"response files audited: {files} (blob parse failures: {parse_fail})")
    print(f"rules: {len(rules)} -> artifacts/{AUDIT_NAME}")
    groups = build_lossy_normalizations(rules)["rules"]
    lossy = [g for g in groups if g["quality"] == "lossy"]
    print(f"groups: {len(groups)} (exact: {len(groups) - len(lossy)}, lossy: {len(lossy)})")


if __name__ == "__main__":
    main()
