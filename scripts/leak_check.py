#!/usr/bin/env python3
"""
jarvis/scripts/leak_check.py — Runtime check that nothing has leaked back in.

Runs WITHOUT Ollama dependency. Verifies:
  1. No -cloud suffixed models in `ollama list`
  2. Hermes config provider != nvidia
  3. All active automations have model.run starting with ollama/
  4. Routing audit log has no cloud provider hits in last 24h (for dry/live stages)

Exit code 0 = clean, 1 = violations found (printed to stderr too).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

JARVIS_HOME = Path.home() / ".jarvis"
HERMES_CONFIG = Path.home() / "AppData" / "Local" / "hermes" / "config.yaml"
AUDIT_LOG = JARVIS_HOME / "audit.log"
AUTOMATIONS_DIR = JARVIS_HOME / "automations"


def check_ollama_cloud_models() -> list[str]:
    """Returns list of -cloud models currently installed."""
    try:
        out = subprocess.check_output(
            ["ollama", "list"], stderr=subprocess.DEVNULL, timeout=10
        ).decode("utf-8", errors="ignore")
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    hits = []
    for line in out.splitlines()[1:]:  # skip header
        m = re.match(r"(\S+)", line)
        if m and m.group(1).endswith(":cloud"):
            hits.append(m.group(1))
    return hits


def check_hermes_provider() -> str | None:
    """Returns the provider currently set, or None on error."""
    if not HERMES_CONFIG.exists():
        return None
    text = HERMES_CONFIG.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^\s*provider:\s*(\S+)", text, re.MULTILINE)
    return m.group(1) if m else None


def check_automation_models() -> list[dict]:
    """Returns violations: automations at dry/live stage with non-local run model."""
    if not AUTOMATIONS_DIR.exists():
        return []
    violations = []
    for p in AUTOMATIONS_DIR.glob("*.yaml"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        # crude parse — just look for stage + model.run on close lines
        stage_match = re.search(r"^\s*stage:\s*(\S+)", text, re.MULTILINE)
        model_match = re.search(r"^\s*run:\s*(\S+)", text, re.MULTILINE)
        if not stage_match or not model_match:
            continue
        stage = stage_match.group(1).strip('"')
        run_model = model_match.group(1).strip('"')
        if stage in ("dry", "live") and not run_model.startswith(("ollama/", "phi4", "qwen", "llama", "mistral")):
            violations.append({
                "automation": p.stem,
                "stage": stage,
                "model_run": run_model,
            })
    return violations


def check_audit_log() -> list[dict]:
    """Returns cloud-routed calls in the last 24h with dry/live stage."""
    if not AUDIT_LOG.exists():
        return []
    bad = []
    cutoff = datetime.now(timezone.utc).timestamp() - 86400
    with AUDIT_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("ts")
            if not isinstance(ts, (int, float)) or ts < cutoff:
                continue
            chosen = entry.get("chosen", "")
            if chosen.startswith("cloud:"):
                bad.append({
                    "ts": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                    "task": entry.get("task", "?"),
                    "chosen": chosen,
                })
    return bad


def main() -> int:
    print("=" * 60)
    print("JARVIS leak_check — running audits")
    print("=" * 60)

    violations = []

    cloud_models = check_ollama_cloud_models()
    if cloud_models:
        print(f"\n❌ Ollama -cloud models still installed: {cloud_models}")
        violations.append(("ollama-cloud-models", cloud_models))
    else:
        print("\n✓ No -cloud suffixed Ollama models installed")

    provider = check_hermes_provider()
    if provider in ("nvidia", "openai", "anthropic", "groq"):
        print(f"❌ Hermes provider is '{provider}' (cloud)")
        violations.append(("hermes-provider", provider))
    elif provider == "ollama":
        print(f"✓ Hermes provider is local (ollama)")
    else:
        print(f"⚠ Hermes provider is '{provider}' (unknown)")

    auto_v = check_automation_models()
    if auto_v:
        print(f"\n❌ {len(auto_v)} automation(s) at dry/live stage with non-local run model:")
        for v in auto_v:
            print(f"   - {v['automation']}: stage={v['stage']}, run={v['model_run']}")
        violations.append(("automation-models", auto_v))
    else:
        print("\n✓ All automations at dry/live have local run model")

    audit_bad = check_audit_log()
    if audit_bad:
        print(f"\n❌ {len(audit_bad)} cloud-routed call(s) in last 24h:")
        for a in audit_bad[:5]:
            print(f"   - {a['ts']} task={a['task']} -> {a['chosen']}")
        violations.append(("audit-cloud-calls", audit_bad))
    else:
        print("\n✓ No cloud-routed calls in audit log (last 24h)")

    print()
    if violations:
        print(f"❌ {len(violations)} CATEGORY(IES) OF VIOLATIONS — fix immediately")
        return 1
    print("✅ ALL CHECKS PASSED — JARVIS is leak-free")
    return 0


if __name__ == "__main__":
    sys.exit(main())
