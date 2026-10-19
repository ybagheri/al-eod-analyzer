"""Plan-compliance check (plan v2.6 §8.3), invoked by `python -m tasks check`.

Checks (each returns a finding or None):
1. STATUS.yaml exists and has the required schema keys.
2. At most one step in_progress, except the allowed parallel pairs (S0+S1).
3. A step marked done must have docs/evidence/<step>.md with required sections.
4. Plan-hash guard: docs/PLAN_V2.sha256 must match docs/PLAN_V2.md, unless an
   ADR in docs/DECISIONS.md references the new hash and the text "user-approved".
5. Frozen Gold-Test manifest hash (docs/GOLD_TEST.sha256), if present, is unchanged.
6. Public-safety scan on the tracked working tree passes.
7. Uncommitted changes to human-sourced labels are not allowed without a
   history entry in the same file (full per-file enforcement lands in S2).
8. Commit message format `S<k>: <summary>` for post-s0 commits.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime
from typing import Any

import public_safety_scan as pss
import yaml

REPO = pss.REPO

REQUIRED_STATUS_KEYS = (
    "schema_version",
    "plan",
    "current_step",
    "steps",
    "last_gate",
    "counts",
    "checks",
)
ALLOWED_PARALLEL_IN_PROGRESS = {frozenset({"S0", "S1"})}
EVIDENCE_SECTIONS = ("Commands run", "Files created/changed", "Metrics", "Deviations", "Open risks")
# Applies to commits made after the S0 enforcement itself exists, i.e. after
# the plan-adoption commit 0dc902f (2026-10-19T11:44:23+03:30); legacy commits
# (pre-plan, often `feat:`/`docs:` style) are exempt.
LEGACY_COMMIT_CUTOFF = datetime.fromisoformat("2026-10-19T08:14:23+00:00")
SYNC_TARGETS = ("README.md", "ROADMAP.md", "HANDOFF.md")


def _git(args: list[str]) -> str:
    out = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO,
        check=True,
    )
    return out.stdout


def check_status_schema(status: dict[str, Any] | None) -> str | None:
    if status is None:
        path = REPO / "docs" / "STATUS.yaml"
        if not path.exists():
            return "STATUS.yaml missing"
        try:
            status = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # yaml errors are fine to expose
            return f"STATUS.yaml not parseable: {exc}"
    if not isinstance(status, dict) or any(k not in status for k in REQUIRED_STATUS_KEYS):
        return f"STATUS.yaml missing required keys {REQUIRED_STATUS_KEYS}"
    steps = status.get("steps")
    if not isinstance(steps, dict) or "S0" not in steps:
        return "STATUS.yaml steps must include S0"
    plan = status.get("plan")
    if not isinstance(plan, dict) or "file" not in plan or "sha256" not in plan:
        return "STATUS.yaml plan.file / plan.sha256 missing"
    return None


def check_in_progress(status: dict[str, Any]) -> str | None:
    in_prog = {k for k, v in status.get("steps", {}).items() if v.get("status") == "in_progress"}
    if len(in_prog) > 1 and frozenset(in_prog) not in ALLOWED_PARALLEL_IN_PROGRESS:
        return f"more than one step in_progress: {sorted(in_prog)}"
    return None


def check_evidence_for_done(status: dict[str, Any]) -> str | None:
    for step, fields in status.get("steps", {}).items():
        if fields.get("status") != "done":
            continue
        path = REPO / "docs" / "evidence" / f"{step}.md"
        if not path.exists():
            return f"step {step} is done but docs/evidence/{step}.md is missing"
        text = path.read_text(encoding="utf-8", errors="replace")
        for section in EVIDENCE_SECTIONS:
            if section.lower() not in text.lower():
                return f"docs/evidence/{step}.md missing section: {section}"
    return None


def check_plan_hash(_status: dict[str, Any] | None = None) -> str | None:
    plan = REPO / "docs" / "PLAN_V2.md"
    sha_file = REPO / "docs" / "PLAN_V2.sha256"
    if not plan.exists() or not sha_file.exists():
        return "docs/PLAN_V2.md or docs/PLAN_V2.sha256 missing"
    digest = hashlib.sha256(plan.read_bytes()).hexdigest()
    if sha_file.read_text(encoding="utf-8").strip() != digest:
        decisions = (REPO / "docs" / "DECISIONS.md").read_text(encoding="utf-8", errors="replace")
        if digest in decisions and "user-approved" in decisions.lower():
            return None
        return "docs/PLAN_V2.md changed without an ADR referencing the new hash (plan-hash guard)"
    return None


def check_gold_test_hash(_status: dict[str, Any] | None = None) -> str | None:
    for manifest, hashfile in ((("artifacts", "gold_set.json"), ("docs", "GOLD_TEST.sha256")),):
        mf = REPO.joinpath(*manifest)
        hf = REPO.joinpath(*hashfile)
        if not hf.exists():
            return None  # Gold-Test not frozen yet
        expected = hf.read_text(encoding="utf-8").strip()
        if not mf.exists() or hashlib.sha256(mf.read_bytes()).hexdigest() != expected:
            return "frozen Gold-Test manifest hash changed (forbidden)"
    return None


def check_public_safety(_status: dict[str, Any] | None = None) -> str | None:
    violations = pss.scan_working_tree()
    if violations:
        summary = "; ".join(f"{v['path']}: {','.join(v['findings'])}" for v in violations[:5])
        return f"public-safety violations ({len(violations)}): {summary}"
    return None


def check_human_label_edits(_status: dict[str, Any] | None = None) -> str | None:
    dirty = [ln for ln in _git(["diff", "--name-only", "HEAD"]).splitlines() if ln.strip()]
    labels = [p for p in dirty if p.startswith("artifacts/labels/")]
    for path in labels:
        full = REPO / path
        if not full.exists():
            continue
        text = full.read_text(encoding="utf-8", errors="replace")
        if '"source": "human"' in text and '"history"' not in text:
            return f"human-sourced label modified without a history entry: {path}"
    return None


def check_commit_format(_status: dict[str, Any] | None = None) -> str | None:
    raw = _git(
        [
            "log",
            "--pretty=%cI%x1f%H%x1f%s%x1e",
            "-15",
        ]
    )
    nonconforming: list[str] = []
    for line in raw.split("\x1e"):
        line = line.strip()
        if not line:
            continue
        try:
            date_s, _sha, subject = line.split("\x1f", 2)
        except ValueError:
            continue
        when = datetime.fromisoformat(date_s)
        if when < LEGACY_COMMIT_CUTOFF:
            continue
        if re.match(r"^S\d+: \S", subject) or subject.startswith(("Merge ", "Revert ")):
            continue
        nonconforming.append(subject)
    if nonconforming:
        return f"commits not in `S<k>: <summary>` format: {nonconforming[:3]}"
    return None


def run_all_checks() -> list[str]:
    findings: list[str] = []
    status: dict[str, Any] | None = None
    path = REPO / "docs" / "STATUS.yaml"
    if path.exists():
        status = yaml.safe_load(path.read_text(encoding="utf-8"))
    for fn in (
        check_status_schema,
        check_in_progress,
        check_evidence_for_done,
        check_plan_hash,
        check_gold_test_hash,
        check_public_safety,
        check_human_label_edits,
        check_commit_format,
    ):
        try:
            finding = fn(status)  # type: ignore[arg-type]
        except Exception as exc:
            finding = f"{fn.__name__} raised: {exc}"
        if finding:
            findings.append(finding)
    return findings


def main() -> int:
    findings = run_all_checks()
    if findings:
        for f in findings:
            print(f"PLAN-COMPLIANCE FAIL: {f}")
        return 1
    print("plan-compliance ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
