"""
jarvis/policy.py — Zero-leak LLM routing policy for JARVIS.

Build phase: cloud models OK (no personal data in prompts).
Run phase:   local Ollama only (PII is now in context).
Override:    explicit `--force local|cloud` flag (Telegram /private|/public
             overrides retired 2026-06-16 — set force explicitly instead).

This module is the single chokepoint for LLM calls.
Any script that wants to talk to an LLM MUST import it from here,
NOT call Ollama/Cloud APIs directly.

Usage:
    from jarvis.policy import call_llm, audit_redact

    # Cloud OK (build mode, no PII)
    response = call_llm(prompt="Write a LinkedIn scraper.", mode="build")

    # Local only (run mode, PII present)
    response = call_llm(
        prompt=f"Summarize: {resume_text}",
        mode="run",
        pii_acknowledged=True,
    )

    # Force local regardless
    response = call_llm(prompt=anything, force="local")

    # Audit a string for PII before deciding
    findings = audit_redact(text)
    if findings.has_pii:
        print(findings.report())
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

JARVIS_HOME = Path(os.environ.get("JARVIS_HOME", Path.home() / ".jarvis"))
AUDIT_LOG = JARVIS_HOME / "audit.log"
POLICY_FILE = JARVIS_HOME / "policy.json"


class Mode(str, Enum):
    BUILD = "build"   # Cloud OK, no PII expected
    RUN = "run"       # Local only, PII present
    HYBRID = "hybrid"  # Decide per-prompt based on content


class Force(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    AUTO = "auto"


DEFAULT_POLICY = {
    "default_mode": "hybrid",
    # JARVIS M0: cloud model list is empty by default (zero-leak floor).
    # When Venu needs a cloud model for a non-PII build task, he appends
    # /public to the command OR sets a temporary env override. There is no
    # default cloud model because there is NO build task that needs cloud by
    # default. To allow cloud: set JARVIS_ALLOW_CLOUD=1 in the env of that
    # one-off session, and pick a model from policy.allowed_cloud_providers.
    "default_cloud_model": "",   # ← empty = block by default
    "default_local_model": "qwen2.5-coder:3b",
    "ollama_url": "http://localhost:11434",
    "allowed_cloud_providers": ["ollama-cloud", "nvidia", "groq"],
    "denied_cloud_providers": ["openai", "anthropic"],
    "denied_cloud_models": [
        # Permanent ban: any -cloud suffixed ollama model name.
        # If ollama-cliaud/minimax-m3, gpt-oss-cloud, etc. leak back in,
        # call_llm() will refuse them.
        "gemma4:31b-cloud", "gpt-oss:120b-cloud", "minimaxai/minimax-m3",
        "minimax-m3:cloud", "phi4-cloud", "qwen-cloud", "llama-cloud",
    ],
    "redaction_aggressiveness": "high",
    "telegram_command_override": False,  # Telegram removed 2026-06-16 (kept for legacy callers)
    "audit_all_calls": True,
}


def load_policy() -> dict:
    if POLICY_FILE.exists():
        return {**DEFAULT_POLICY, **json.loads(POLICY_FILE.read_text())}
    JARVIS_HOME.mkdir(parents=True, exist_ok=True)
    POLICY_FILE.write_text(json.dumps(DEFAULT_POLICY, indent=2))
    return DEFAULT_POLICY


POLICY = load_policy()


# ---------------------------------------------------------------------------
# PII detection
# ---------------------------------------------------------------------------

PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email", re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")),
    ("phone_in", re.compile(r"\b(?:\+91[\s\-]?)?[6-9]\d{9}\b")),        # Indian mobile
    ("phone_intl", re.compile(r"\+\d{1,3}[\s\-]?\d{4,14}")),
    ("aadhaar", re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")),
    ("pan", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("ssn_us", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ \-]?){13,16}\b")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("path_user", re.compile(r"[A-Za-z]:\\\\Users\\\\[A-Za-z]+", re.IGNORECASE)),  # C:\Users\Venu
    ("url_pii", re.compile(r"https?://[^\s]*pvgreddy[^\s]*", re.IGNORECASE)),
]

# Domain-specific for Venu — what's sensitive in his projects
VENU_DOMAIN_KEYWORDS = [
    "resume", "cv ", "vpaulreddy", "pvgreddy", "venugopalreddy",
    "palugulla", "galgotias", "MCA",
    "salary", "ctc", "package",
    "gmail.com", "smtp.gmail", "app password", "app_password",
    "telegram bot token", "telegram_bot_token",
    "linkedin.com/in/",  # his profile URL
    "phone", "address",
    "@gmail", ".env",
    "/c/Users/Venu", "C:\\Users\\Venu",
]

# Public-domain (safe for cloud)
PUBLIC_KEYWORDS = [
    "python", "javascript", "rust ", "golang",
    "stackoverflow", "github.com/", "arxiv",
    "wikipedia", "docs.", "tutorial",
    "regex pattern", "algorithm",
    "weather", "news ", "trends",
]


@dataclass
class PIIFinding:
    pii_types: list[str] = field(default_factory=list)
    domain_hits: list[str] = field(default_factory=list)
    matches: list[tuple[str, str]] = field(default_factory=list)  # (type, value)

    @property
    def has_pii(self) -> bool:
        return bool(self.pii_types or self.domain_hits)

    @property
    def has_structured_pii(self) -> bool:
        # Strong signal (email/phone/aadhaar/pan/path) — definitely local only
        return bool(self.pii_types)

    def report(self) -> str:
        out = []
        if self.pii_types:
            out.append(f"structured PII types: {sorted(set(self.pii_types))}")
        if self.domain_hits:
            out.append(f"Venu-domain keywords: {sorted(set(self.domain_hits))}")
        if self.matches:
            shown = [(t, v[:8] + "...") for t, v in self.matches[:5]]
            out.append(f"matches: {shown}")
        return " | ".join(out) if out else "(no PII detected)"


def audit_redact(text: str, aggressiveness: str | None = None) -> PIIFinding:
    """Scan text for PII. Returns findings. Use report() to log."""
    level = aggressiveness or POLICY["redaction_aggressiveness"]
    f = PIIFinding()
    if not text:
        return f

    for pii_type, pattern in PII_PATTERNS:
        for m in pattern.finditer(text):
            f.pii_types.append(pii_type)
            f.matches.append((pii_type, m.group(0)))

    # Always check Venu-domain keywords (high signal)
    text_lc = text.lower()
    for kw in VENU_DOMAIN_KEYWORDS:
        if kw.lower() in text_lc:
            f.domain_hits.append(kw)

    if level == "high":
        # Even more conservative: any single mention of a strong term = PII
        pass
    elif level == "medium":
        # Whitelist strong public-domain
        public_count = sum(1 for k in PUBLIC_KEYWORDS if k in text_lc)
        if public_count >= 3 and not f.pii_types:
            f.domain_hits.clear()

    # Dedup
    f.pii_types = sorted(set(f.pii_types))
    f.domain_hits = sorted(set(f.domain_hits))
    return f


def redact_for_cloud(text: str, finding: PIIFinding) -> str:
    """Replace PII with safe placeholder before sending to cloud."""
    out = text
    for pii_type in finding.pii_types:
        for p_type, pattern in PII_PATTERNS:
            if pii_type == p_type:
                out = pattern.sub(f"[{pii_type.upper()}_REDACTED]", out)
    # Venu-domain plain keywords → underscore them but keep readable
    for kw in finding.domain_hits:
        out = re.sub(re.escape(kw), f"[{kw.upper()}_REDACTED]", out, flags=re.IGNORECASE)
    return out


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def _audit(entry: dict) -> None:
    if not POLICY["audit_all_calls"]:
        return
    entry["ts"] = int(time.time())
    entry["hash"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    JARVIS_HOME.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")


# ---------------------------------------------------------------------------
# Workspace layout guard — avoid re-introducing ~/.openclaw/workspace/ code
# ---------------------------------------------------------------------------

# Anything under this prefix in an automation path is now considered legacy.
# Auditing-side reference: see 2026-06-14 consolidation notes in
# ~/.jarvis/automations/README.md
LEGACY_OPENCLAW_WORKSPACE = Path.home() / ".openclaw" / "workspace"


def warn_on_legacy_openclaw_path(path: str | os.PathLike) -> None:
    """
    Warn (and audit-log) when an automation references the legacy
    ~/.openclaw/workspace/ tree. Code lives at ~/.jarvis/automations/ now.
    Hard-fails only when POLICY["strict_workspace_layout"] is True; otherwise
    just logs a soft warning.

    Use this in automations that resolve a project base directory, or call
    it from a startup hook to catch regressions early.

    >>> warn_on_legacy_openclaw_path("C:/Users/Venu/.openclaw/workspace/job-automation/run.py")
    WARNING: legacy openclaw path ...
    """
    try:
        p = Path(path).expanduser().resolve()
    except (OSError, ValueError):
        return

    legacy_root = LEGACY_OPENCLAW_WORKSPACE.expanduser().resolve(strict=False)

    try:
        p.relative_to(legacy_root)
    except ValueError:
        return  # not under the legacy tree — fine

    msg = (
        f"legacy openclaw workspace path in automation: {p}. "
        f"Code should live under {Path.home() / '.jarvis' / 'automations'}. "
        f"See ~/.jarvis/automations/README.md (consolidated 2026-06-14)."
    )
    print(f"[jarvis-policy] WARNING: {msg}", file=sys.stderr)

    _audit(
        {
            "event": "legacy_workspace_path",
            "path": str(p),
            "legacy_root": str(legacy_root),
            "strict": POLICY.get("strict_workspace_layout", False),
        }
    )

    if POLICY.get("strict_workspace_layout", False):
        raise RuntimeError(msg)


def _scan_legacy_projects(legacy_workspace: Path) -> list[str]:
    """Finds remaining projects in the legacy workspace."""
    legacy_projects_remaining = []
    if legacy_workspace.exists():
        # Anything that looks like an automation project (has run.py or cron.yaml
        # at top level) under .openclaw/workspace/ is a regression.
        for child in legacy_workspace.iterdir():
            if child.is_dir() and any((child / marker).exists()
                                      for marker in ("run.py", "cron.yaml")):
                legacy_projects_remaining.append(child.name)
    return legacy_projects_remaining


def _scan_legacy_refs_in_source(automations_root: Path) -> list[tuple[str, int, str]]:
    """Finds legacy path references in automation source files."""
    legacy_refs = []
    if automations_root.exists():
        for py in automations_root.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if "openclaw/workspace" in line or "openclaw\\workspace" in line:
                    legacy_refs.append((str(py), n, line.strip()))
    return legacy_refs


def audit_workspace_layout() -> dict:
    """
    One-shot scan of ~/.jarvis/automations/ and ~/.openclaw/workspace/ used by
    jarvis_audit.py / scheduled leak_check.py. Returns counts and the list of
    legacy paths still referenced (so you can fix them).

    Returns:
        {
            "automations_root": str,
            "legacy_root": str,
            "automations": [str project names],
            "legacy_projects_remaining": [str],
            "legacy_refs_in_source": [(file, line_no, line_text), ...],
            "strict": bool,
            "ok": bool,
        }
    """
    automations_root = JARVIS_HOME / "automations"
    strict = POLICY.get("strict_workspace_layout", False)

    legacy_projects_remaining = _scan_legacy_projects(LEGACY_OPENCLAW_WORKSPACE)
    legacy_refs = _scan_legacy_refs_in_source(automations_root)

    ok = (not legacy_projects_remaining) and (not legacy_refs)
    return {
        "automations_root": str(automations_root),
        "legacy_root": str(LEGACY_OPENCLAW_WORKSPACE),
        "automations": sorted(p.name for p in automations_root.iterdir()
                              if p.is_dir()) if automations_root.exists() else [],
        "legacy_projects_remaining": legacy_projects_remaining,
        "legacy_refs_in_source": legacy_refs,
        "strict": strict,
        "ok": ok,
    }


# ---------------------------------------------------------------------------
# The main call
# ---------------------------------------------------------------------------

@dataclass
class LLMResult:
    text: str
    model: str
    provider: str       # "local" | "cloud"
    redacted: bool
    finding: PIIFinding
    latency_s: float
    cost_estimate_usd: float = 0.0


def _call_ollama(prompt: str, model: str, ollama_url: str, timeout_s: int | None = None) -> tuple[str, float]:
    """Local Ollama call. NEVER raises to caller — returns empty on failure.

    timeout_s defaults to env JARVIS_OLLAMA_TIMEOUT_S (120s) so an automation
    like prep_generator (long system prompt for structured output) can opt
    for more headroom via either:
      * `policy.call_llm(..., timeout_s=240)` per call, or
      * `export JARVIS_OLLAMA_TIMEOUT_S=240` for an entire session.
    The override is per-call when known; per-session when sweeping across many.
    """
    if timeout_s is None:
        try:
            timeout_s = int(os.environ.get("JARVIS_OLLAMA_TIMEOUT_S", "120"))
        except (TypeError, ValueError):
            timeout_s = 120
    t0 = time.time()
    try:
        r = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout_s,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("response", ""), time.time() - t0
    except requests.exceptions.ReadTimeout:
        # Bubble back a sentinel so call_llm() can audit-log the timeout.
        # Returning empty string on plain NetworkError would mask latency
        # regressions; we instead raise so the chokepoint can record it.
        raise ReadTimeoutError(prompt_len=len(prompt), model=model, timeout_s=timeout_s)


class ReadTimeoutError(Exception):
    """Raised when an ollama request exceeds its timeout budget.

    Carries enough context to make audit-log + debugging deterministic.
    """
    def __init__(self, prompt_len: int, model: str, timeout_s: int):
        super().__init__(
            f"ollama read timeout after {timeout_s}s on model={model} "
            f"(prompt_len={prompt_len})"
        )
        self.prompt_len = prompt_len
        self.model = model
        self.timeout_s = timeout_s


def _call_cloud(prompt: str, model: str) -> tuple[str, float]:
    """Cloud call. Stub — user must implement Ollama-cloud / NVIDIA / Groq clients.
    For now, we funnel ALL cloud through Ollama's cloud mode if model ends in -cloud.
    Extend this with provider-specific clients as needed.
    """
    # Ollama cloud passthrough (the local Ollama binary handles this)
    return _call_ollama(prompt, model, POLICY["ollama_url"])


def call_llm(
    prompt: str,
    *,
    mode: str = "hybrid",
    force: str = "auto",
    pii_acknowledged: bool = False,
    task_label: str = "",
    on_pii_refused: Optional[Callable[[PIIFinding], None]] = None,
    timeout_s: Optional[int] = None,
) -> LLMResult:
    """The single chokepoint. Every JARVIS-internal LLM call goes through here.

    Args:
        prompt: User prompt.
        mode: "build" (cloud OK), "run" (PII expected, local only),
              "hybrid" (decide per-prompt).
        force: "local" | "cloud" | "auto".
        pii_acknowledged: If True, caller attests PII is present and wants local.
                          Skips redacting but still routes to local.
        task_label: For audit ("resume_tailor_v2" etc).
        timeout_s: Per-call ollama request timeout override (seconds). If None,
                   reads env JARVIS_OLLAMA_TIMEOUT_S (default 120). Use this
                   when your prompt is large or structured-output templates
                   are slow: `call_llm(..., timeout_s=300)`.

    Behavior:
        1. Audit prompt for PII.
        2. If force == "local" → local only, always.
        3. If mode == "build" AND no PII found → cloud allowed.
        4. If PII found → redact and reroute to local (still answers, but cleaner).
        5. If mode == "run" → local only.
        6. Audit log entry always written.
    """
    policy = POLICY
    finding = audit_redact(prompt, policy["redaction_aggressiveness"])

    decision_log = {
        "task": task_label,
        "mode": mode,
        "force": force,
        "pii_acknowledged": pii_acknowledged,
        "finding": finding.report(),
        # Don't log the full prompt — just a hash-prefix for traceability
        "prompt_sha8": hashlib.sha256(prompt.encode()).hexdigest()[:8],
        "prompt_len": len(prompt),
    }

    # Rule engine — apply in order
    provider = None
    model = None
    redacted = False

    if force == "local":
        provider = "local"
        model = policy["default_local_model"]
    elif force == "cloud":
        provider = "cloud"
        model = policy["default_cloud_model"]
    elif mode == "run":
        provider = "local"
        model = policy["default_local_model"]
        if finding.has_structured_pii and not pii_acknowledged:
            decision_log["note"] = "run mode + structured PII + not acknowledged -> forced local"
    elif mode == "build":
        if finding.has_structured_pii:
            # Build claimed "no PII", but PII was found. Refuse cloud.
            if on_pii_refused:
                on_pii_refused(finding)
            prompt_safe = redact_for_cloud(prompt, finding)
            provider = "local"
            model = policy["default_local_model"]
            redacted = True
            decision_log["note"] = (
                "build mode but PII detected -> redacted+local "
                "(speaker must have lied about build cleanliness)"
            )
        else:
            # Check env override — /public or JARVIS_ALLOW_CLOUD=1
            env_allow = os.environ.get("JARVIS_ALLOW_CLOUD", "").strip() == "1"
            if not env_allow or not policy.get("default_cloud_model"):
                # Default: build without env-allow = still local, defense in depth
                provider = "local"
                model = policy["default_local_model"]
                decision_log["note"] = (
                    "build mode but JARVIS_ALLOW_CLOUD not set, "
                    "defaulting to local"
                )
            else:
                # Check deny-list
                cm = policy.get("default_cloud_model", "")
                if any(d.lower() in cm.lower() for d in policy.get("denied_cloud_models", [])):
                    provider = "local"
                    model = policy["default_local_model"]
                    decision_log["note"] = (
                        f"cloud model {cm} on denied-list, routed local"
                    )
                else:
                    provider = "cloud"
                    model = policy["default_cloud_model"]
    else:  # hybrid
        if finding.has_pii:
            # PII found → local
            prompt_safe = prompt
            if not pii_acknowledged:
                # Redact defensively even on local — defense in depth
                prompt_safe = redact_for_cloud(prompt, finding)
                redacted = True
            provider = "local"
            model = policy["default_local_model"]
        else:
            provider = "cloud"
            model = policy["default_cloud_model"]

    decision_log["chosen"] = f"{provider}:{model}"
    _audit(decision_log)

    # Execute
    text_to_send = redact_for_cloud(prompt, finding) if redacted else prompt
    if provider == "local":
        try:
            text, latency = _call_ollama(text_to_send, model, policy["ollama_url"], timeout_s=timeout_s)
        except ReadTimeoutError as te:
            # Audit the timeout — this is signal for future tuning. Caller
            # still sees an empty-text LLMResult back, not an exception, so
            # existing automations don't need error-handling rewrites.
            _audit({
                "task": task_label,
                "event": "ollama_timeout",
                "model": model,
                "prompt_len": te.prompt_len,
                "timeout_s": te.timeout_s,
                "latency_s": float(te.timeout_s),
            })
            return LLMResult(
                text="",
                model=model,
                provider="local",
                redacted=redacted,
                finding=finding,
                latency_s=float(te.timeout_s),
            )
    else:
        text, latency = _call_cloud(text_to_send, model)

    return LLMResult(
        text=text,
        model=model,
        provider=provider,
        redacted=redacted,
        finding=finding,
        latency_s=latency,
    )


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    test = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Write me a Python LinkedIn scraper using Selenium."
    )
    f = audit_redact(test)
    print("Audit:", f.report())
    print(f"Has PII: {f.has_pii}")
    print(f"Has structured PII: {f.has_structured_pii}")
    print()
    res = call_llm(test, mode="build", task_label="cli-test")
    print(f"Routed to: {res.provider}:{res.model} (redacted={res.redacted})")
    print(f"Latency: {res.latency_s:.2f}s")
    print(f"Response preview: {res.text[:300]}...")
