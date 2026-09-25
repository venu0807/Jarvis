"""
jarvis/lifecycle.py — Stage promotion engine for JARVIS automations.

Stages: draft -> test -> stage -> dry -> live
Only draft/test/stage allow cloud models (build phase).
dry/live = local Ollama only (run phase).

Centralizes all stage-guard logic so /jarvis/automations/*.yaml files
stay declarative and the lifecycle is the single source of truth.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

JARVIS_HOME = Path.home() / ".jarvis"
AUTOMATIONS_DIR = JARVIS_HOME / "automations"
ARCHIVE_DIR = AUTOMATIONS_DIR / "archive"
LOGS_DIR = JARVIS_HOME / "logs"


class Stage(str, Enum):
    DRAFT = "draft"
    TEST = "test"
    STAGE = "stage"
    DRY = "dry"
    LIVE = "live"


# Promotion chain — skipping forbidden
ORDER = [Stage.DRAFT, Stage.TEST, Stage.STAGE, Stage.DRY, Stage.LIVE]


@dataclass
class PromotionResult:
    ok: bool
    message: str
    from_stage: Optional[str] = None
    to_stage: Optional[str] = None


def _load(name: str) -> dict:
    p = AUTOMATIONS_DIR / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"automation not found: {name}")
    # Tiny YAML loader — only flat key-value + list-of-strings + nested dicts.
    # Sufficient for our manifest schema. If we ever hit complex nesting, swap in PyYAML.
    text = p.read_text(encoding="utf-8")
    return _mini_yaml(text)


def _save(name: str, data: dict) -> None:
    p = AUTOMATIONS_DIR / f"{name}.yaml"
    p.write_text(_dump_yaml(data), encoding="utf-8")


def _mini_yaml(text: str) -> dict:
    """Parse the simple YAML we generate. No PyYAML dependency by design."""
    root: dict = {}
    stack: list[tuple[int, dict | list]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.lstrip().rstrip()
        # pop stack until parent is at lower indent
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else root
        if line.startswith("- "):
            # list item
            val = line[2:].strip().strip('"').strip("'")
            if isinstance(parent, list):
                parent.append(val)
        elif ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if v == "":
                # nested dict or list — peek next indent; default to dict
                new = {}
                stack.append((indent, new))
                parent[k] = new
            elif v.startswith("[") and v.endswith("]"):
                # inline list
                items = [s.strip().strip('"').strip("'") for s in v[1:-1].split(",") if s.strip()]
                parent[k] = items
            elif v.lower() in ("true", "false"):
                parent[k] = (v.lower() == "true")
            elif v.startswith('"') and v.endswith('"'):
                parent[k] = v[1:-1]
            else:
                parent[k] = v
    return root


def _dump_yaml(data: dict, indent: int = 0) -> str:
    out = []
    pad = "  " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            out.append(f"{pad}{k}:")
            out.append(_dump_yaml(v, indent + 1))
        elif isinstance(v, list):
            if all(isinstance(x, str) for x in v):
                items = ", ".join(x for x in v)
                out.append(f"{pad}{k}: [{items}]")
            else:
                out.append(f"{pad}{k}:")
                for item in v:
                    out.append(f"{pad}  - {item}")
        elif isinstance(v, bool):
            out.append(f"{pad}{k}: {str(v).lower()}")
        elif isinstance(v, str):
            out.append(f"{pad}{k}: \"{v}\"")
        else:
            out.append(f"{pad}{k}: {v}")
    return "\n".join(out) + "\n"


def _next_stage(current: Stage) -> Optional[Stage]:
    try:
        idx = ORDER.index(current)
        return ORDER[idx + 1] if idx + 1 < len(ORDER) else None
    except ValueError:
        return None


def promote(name: str, target: Stage, *, dry_history_required: int = 3) -> PromotionResult:
    """Promote name to target stage. Enforces chain + critical dry->live gate.

    Returns PromotionResult with ok and message. Never raises for normal
    failures — only for IO/programming errors.
    """
    try:
        data = _load(name)
    except FileNotFoundError as e:
        return PromotionResult(False, str(e))

    current_str = data.get("stage", Stage.DRAFT.value)
    try:
        current = Stage(current_str)
    except ValueError:
        return PromotionResult(False, f"unknown current stage: {current_str}")

    # Backward / same-stage is always allowed
    if target == current:
        return PromotionResult(True, f"already at {current.value}", current.value, current.value)

    # Find target index
    try:
        target_idx = ORDER.index(target)
    except ValueError:
        return PromotionResult(False, f"unknown target stage: {target}")

    current_idx = ORDER.index(current)

    # Backward (rollback) is always allowed
    if target_idx < current_idx:
        data["stage"] = target.value
        data["updated"] = _now()
        _save(name, data)
        return PromotionResult(
            True, f"rolled back {current.value} -> {target.value}",
            current.value, target.value
        )

    # Forward: must be exactly next stage
    expected_next = _next_stage(current)
    if expected_next is None:
        return PromotionResult(False, f"already at terminal stage: {current.value}")
    if target != expected_next:
        return PromotionResult(
            False,
            f"cannot skip — current={current.value}, target={target.value}; "
            f"next allowed is {expected_next.value}"
        )

    # Critical gate: dry -> live needs 3 dry PASS + 0 leak warnings + <24h
    if current == Stage.DRY and target == Stage.LIVE:
        history = data.get("dry_runs", {}).get("history", [])
        passed = [h for h in history if h.get("outcome") == "PASS"]

        if len(passed) < dry_history_required:
            return PromotionResult(
                False,
                f"need {dry_history_required} dry PASS, have {len(passed)}"
            )

        recent = history[-dry_history_required:]
        if any(h.get("leak_warnings") for h in recent):
            return PromotionResult(
                False,
                "last 3 dry runs had leak warnings"
            )

        if recent:
            last_ts = recent[-1].get("ran_at")
            if last_ts:
                try:
                    last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                    age_h = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                    if age_h > 24:
                        return PromotionResult(
                            False,
                            f"last dry run is {age_h:.1f}h old (>24h stale)"
                        )
                except Exception:
                    pass

    data["stage"] = target.value
    data["updated"] = _now()
    _save(name, data)
    return PromotionResult(
        True, f"promoted {current.value} -> {target.value}",
        current.value, target.value
    )


def record_dry_run(
    name: str,
    *,
    outcome: str,            # PASS | FAIL | LEAK_WARN
    duration_ms: int,
    record_count: int = 0,
    error: Optional[str] = None,
    leak_warnings: list[str] | None = None,
    summary: str = "",
) -> None:
    """Append a dry-run entry to the automation's manifest."""
    data = _load(name)
    history = data.setdefault("dry_runs", {}).setdefault("history", [])
    entry = {
        "ran_at": _now(),
        "outcome": outcome,
        "duration_ms": duration_ms,
        "record_count": record_count,
        "leak_warnings": leak_warnings or [],
    }
    if error:
        entry["error"] = error
    if summary:
        entry["summary"] = summary
    history.append(entry)
    data["updated"] = _now()
    _save(name, data)


def tear_down(name: str, *, archive: bool = True) -> PromotionResult:
    """Rollback to draft + archive manifest if requested. Never deletes."""
    try:
        data = _load(name)
    except FileNotFoundError as e:
        return PromotionResult(False, str(e))

    if archive:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        src = AUTOMATIONS_DIR / f"{name}.yaml"
        dst = ARCHIVE_DIR / f"{name}.{ts}.yaml"
        shutil.copy2(src, dst)

    # Reset to draft
    data["stage"] = Stage.DRAFT.value
    data["updated"] = _now()
    if "schedule" in data:
        data["schedule"] = None  # disable cron registration
    data["torn_down_at"] = _now()
    _save(name, data)
    return PromotionResult(True, f"torn down to draft, archived")


def health_check(name: str) -> dict:
    """Returns a snapshot of an automation's posture."""
    try:
        data = _load(name)
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}

    cloud_violation = False
    run_model = data.get("models", {}).get("run", "")
    if data.get("stage") in (Stage.DRY.value, Stage.LIVE.value):
        if not run_model.startswith(("ollama/", "phi4", "qwen", "llama", "mistral")):
            cloud_violation = True

    # Last dry run age
    last_dry = None
    history = data.get("dry_runs", {}).get("history", [])
    if history:
        try:
            last_dt = datetime.fromisoformat(history[-1]["ran_at"].replace("Z", "+00:00"))
            last_dry = {
                "ran_at": history[-1]["ran_at"],
                "outcome": history[-1].get("outcome"),
                "age_h": round(
                    (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600, 1
                ),
            }
        except Exception:
            pass

    return {
        "ok": True,
        "name": name,
        "stage": data.get("stage", Stage.DRAFT.value),
        "model_run": run_model,
        "model_build": data.get("models", {}).get("build", ""),
        "schedule": data.get("schedule"),
        "last_dry": last_dry,
        "cloud_violation": cloud_violation,
        "draft_history_count": len(data.get("dry_runs", {}).get("history", [])),
    }


def list_all() -> list[dict]:
    AUTOMATIONS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in AUTOMATIONS_DIR.glob("*.yaml"):
        if p.parent.name == "archive":
            continue
        try:
            out.append(health_check(p.stem))
        except Exception as e:
            out.append({"ok": False, "name": p.stem, "error": str(e)})
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for h in list_all():
            print(json.dumps(h, indent=2))
    elif cmd == "show" and len(sys.argv) > 2:
        print(json.dumps(health_check(sys.argv[2]), indent=2))
    elif cmd == "promote" and len(sys.argv) > 3:
        r = promote(sys.argv[2], Stage(sys.argv[4] if len(sys.argv) > 4 else sys.argv[3]))
        print(json.dumps({"ok": r.ok, "msg": r.message}, indent=2))
    else:
        print("usage: lifecycle.py [list|show NAME|promote NAME STAGE]")
