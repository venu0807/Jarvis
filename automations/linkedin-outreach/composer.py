"""composer.py — Generate personalized cold emails via JARVIS policy.

Before 2026-06-14: this module called `ollama.generate()` directly with a
fallback chain that put cloud models first. Every cold email sent recruiter
names, your persona ("Venu"), and LinkedIn post content to a public LLM —
a strict-zero-leak violation.

Now: every call is routed through `~/.jarvis/policy.call_llm()` with
mode="run", which means:
  * PII in the prompt → policy refuses to use any cloud model (forced local)
  * If user explicitly sets JARVIS_ALLOW_CLOUD=1 for a one-off build, call_llm
    falls back to its normal hybrid behaviour
  * Audit-logged: `~/.jarvis/audit.log` gets one row per generation with model,
    provider, latency, PII finding summary

Cloud models were previously the default fallback. They are now opt-in only.
"""

import os
import sys
import time
import random
from pathlib import Path
from typing import Optional, List

# Re-route through the JARVIS chokepoint. Hard error if policy is missing —
# means someone moved / deleted ~/.jarvis/policy.py. We do not want silent
# direct-ollama fallback because that is the very behaviour we're fixing.
try:
    # Resolve project root relative to this script — always correct.
    # NOTE: os.environ.get("JARVIS_HOME") is NOT used here because it may
    # point to ~/.jarvis (doesn't exist) instead of the actual project root.
    JARVIS_HOME = str(Path(__file__).resolve().parent.parent.parent)
    if JARVIS_HOME not in sys.path:
        sys.path.insert(0, JARVIS_HOME)
    from policy import call_llm, audit_redact   # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "FATAL: jarvis composer cannot import ~/.jarvis/policy.call_llm. "
        "Strict-zero-leak: refusing to fall back to direct ollama calls. "
        f"Original error: {e!r}"
    )


# Default LOCAL chain (no cloud). Cloud is opt-in via JARVIS_ALLOW_CLOUD=1.
# Ordered fastest local → most reliable. Same order the user previously
# chose when forcing local-only via OLLAMA_FALLBACK_CHAIN.
DEFAULT_LOCAL_CHAIN = [
    "qwen2.5-coder:7b",   # good at structured prose
    "phi4-mini:latest",   # fastest on this box
]

# Allow override via OLLAMA_FALLBACK_CHAIN for ops tweaks (comma-separated).
def _resolve_chain() -> List[str]:
    env = os.getenv("OLLAMA_FALLBACK_CHAIN", "")
    if env:
        return [m.strip() for m in env.split(",") if m.strip()]
    return list(DEFAULT_LOCAL_CHAIN)


def _cloud_is_allowed() -> bool:
    """True only when the user explicitly opted in for this session."""
    return os.environ.get("JARVIS_ALLOW_CLOUD", "").strip() in ("1", "true", "yes")


def _strip_cloud_entries(chain: List[str]) -> List[str]:
    """Drop any '-cloud' suffixed model from a chain unless cloud is allowed."""
    if _cloud_is_allowed():
        return chain
    cleaned = []
    dropped = []
    for m in chain:
        # Conservative: any 'cloud' substring in the model name
        if "cloud" in m.lower():
            dropped.append(m)
        else:
            cleaned.append(m)
    if dropped:
        print(
            f"  [jarvis-policy] stripped cloud models from chain (no "
            f"JARVIS_ALLOW_CLOUD): {dropped}. Set JARVIS_ALLOW_CLOUD=1 for a "
            f"one-off build session if you really want cloud.",
            file=sys.stderr,
        )
    return cleaned


def _try_model_via_policy(model: str, prompt: str, recruiter_name: str) -> Optional[str]:
    """
    Send the prompt to `model` via jarvis.policy.call_llm().
    mode="run" forces the policy to use a local-only model when PII is
    detected; the policy's PII detector triggers on the recruiter's name
    and any "Venu"-class identifiers. The model arg we pass is a *hint*;
    the policy may override it (notably: cloud → local when PII detected).
    """
    t0 = time.time()
    try:
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="auto",
            pii_acknowledged=True,           # we KNOW PII is in the prompt
            task_label=f"cold_email:{recruiter_name}",
        )
    except Exception as e:
        print(f"  ⚠ {model} → policy refused: {type(e).__name__}: {str(e)[:120]}")
        return None

    elapsed = time.time() - t0
    body = (result.text or "").strip()
    if not body:
        print(f"  ⚠ {model}: empty response ({elapsed:.1f}s)")
        return None
    print(
        f"  ✅ {result.model}: {len(body)} chars in {elapsed:.1f}s "
        f"[provider={result.provider}, redacted={result.redacted}]"
    )
    return body


def _try_model(model, prompt, timeout_s=90):
    """DEPRECATED — kept only as a safety net for import-time tests.

    All real generation goes through `_try_model_via_policy` which routes
    through `~/.jarvis/policy.call_llm()`. This wrapper now refuses to call
    ollama directly outside that policy — a direct-ollama call here would
    silently bypass the zero-leak audit log. Hard error.
    """
    raise SystemExit(
        "FATAL: composer._try_model called directly. "
        "All generation must go through jarvis.policy.call_llm() "
        "(see _try_model_via_policy). Refusing to bypass."
    )


def _build_prompt(recruiter_name: str, post_text: str, opener: str, closer: str) -> str:
    """Build the cold-email prompt with opener/closer variance."""
    return f"""You are a fresher Python/Django/AI Developer writing a personalized cold email to a recruiter.

Recruiter's Name: {recruiter_name}
LinkedIn Post Content: {post_text}

Write a 3-paragraph professional cold email:
- Paragraph 1 open with: {opener}
- Paragraph 2: Briefly highlight skills in Python, Django, React/JavaScript, ML/CNN (whichever fits the post).
- Paragraph 3 close with: {closer}

Rules:
- Professional and concise (max 200 words).
- No placeholders like [Name] — sign off as "Venu".
- Do NOT include the subject line, just the body.
- Do NOT echo the prompt back. Start directly with the email body."""


_OPENERS = [
    "I came across your recent LinkedIn post and the role caught my attention.",
    "Your recent post on LinkedIn stood out to me as a strong match for my background.",
    "I saw your LinkedIn update about this opening and wanted to reach out directly.",
    "Noticed your recent post while scrolling LinkedIn — the role describes exactly what I do.",
    "Your recent LinkedIn post about this opening resonated with my project experience.",
]

_CLOSERS = [
    "I've attached my resume for your review. Would a 15-minute call this week work?",
    "Resume attached for context. Happy to share more details over a quick call.",
    "My resume is attached. Could we schedule a brief introduction call?",
    "Resume attached. I'm flexible on timing for a short introductory chat.",
    "Take a look at the attached resume when convenient. Looking forward to hearing back.",
]


def generate_cold_email(post_text, recruiter_name):
    """Generate a personalized cold email through JARVIS policy.

    Returns the email body, or None if every model in the chain failed.
    All calls are routed through `~/.jarvis/policy.call_llm()` with
    mode="run" — strict-zero-leak by default. With PII in the prompt the
    policy will refuse any cloud model and force local-only execution.
    """
    chain = _strip_cloud_entries(_resolve_chain())
    if not chain:
        print("  ❌ NO models left in chain (all were 'cloud' and JARVIS_ALLOW_CLOUD is unset).")
        return None

    # opener/closer variance so identical engines output distinct emails
    opener = random.choice(_OPENERS)
    closer = random.choice(_CLOSERS)
    prompt = _build_prompt(recruiter_name, post_text, opener, closer)

    print(
        f"  🤖 generating email for {recruiter_name!r} "
        f"(policy-routed; chain try-order: {' → '.join(chain)})"
    )

    for model in chain:
        # The 'model' arg is a hint — call_llm() will still enforce mode/run
        # audit-logging and PII rules. If policy decides to swap the model
        # because the requested one is denied, we get the actual model back
        # in result.model and continue.
        body = _try_model_via_policy(model, prompt, recruiter_name)
        if body:
            return body

    print(f"  ❌ ALL models failed for {recruiter_name!r}. Audit-logged in ~/.jarvis/audit.log.")
    return None
