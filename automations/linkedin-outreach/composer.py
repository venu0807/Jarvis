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

UPDATE 2026-08-21: Added support for 5 email templates (T1-T5) per 2-month
job hunt plan. Templates live in templates.py and can be selected via
the template_id parameter.
"""

import os
import sys
import time
import random
import json
from pathlib import Path
from typing import Optional, List

# Re-route through the JARVIS chokepoint. Hard error if policy is missing —
# means someone moved / deleted ~/.jarvis/policy.py. We do not want silent
# direct-ollama fallback because that is the very behaviour we're fixing.
try:
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
DEFAULT_LOCAL_CHAIN = [
    "qwen2.5-coder:3b",   # good at structured prose, fast on 8 GB RAM
    "llama3.2:3b",        # fallback
]

def _resolve_chain() -> List[str]:
    env = os.getenv("OLLAMA_FALLBACK_CHAIN", "")
    if env:
        return [m.strip() for m in env.split(",") if m.strip()]
    return list(DEFAULT_LOCAL_CHAIN)


def _cloud_is_allowed() -> bool:
    return os.environ.get("JARVIS_ALLOW_CLOUD", "").strip() in ("1", "true", "yes")


def _strip_cloud_entries(chain: List[str]) -> List[str]:
    if _cloud_is_allowed():
        return chain
    cleaned = []
    dropped = []
    for m in chain:
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
    t0 = time.time()
    try:
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="auto",
            pii_acknowledged=True,
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
    """DEPRECATED — all generation must go through _try_model_via_policy."""
    raise SystemExit(
        "FATAL: composer._try_model called directly. "
        "All generation must go through jarvis.policy.call_llm()."
    )


def _build_prompt(
    recruiter_name: str,
    post_text: str,
    bio_text: str,
    portfolio_text: str,
    template_id: str = "T2",
) -> str:
    """Build the cold-email prompt using one of 5 templates (T1-T5)."""

    first_name = recruiter_name.split()[0] if recruiter_name else "there"

    from templates import get_template
    template_body = get_template(template_id)

    return f"""You are an AI assistant helping a candidate write a personalized cold email/message to a recruiter on LinkedIn.

Recruiter's Name: {recruiter_name}
LinkedIn Post Content: {post_text}
Recruiter Bio: {bio_text}

Use EXACTLY the following template structure (template {template_id}), filling in placeholders based on the LinkedIn post and bio:

{template_body}

Portfolio (cite 1-2 projects in the email body when relevant):
{portfolio_text}

Placeholders to fill:
- {{first_name}}: Use first name. Default: {first_name}
- {{role}}: Job title from post. Default: "a software engineering role"
- {{company}}: Company name from post. Default: "your team"
- {{specific_thing}}: One specific thing they did/posted. Reference something concrete from their post or bio.

Rules:
- Output starts with "Subject: " on the very first line.
- Subject should be <=60 chars and mention the role/company.
- Body should be <=300 words for DM-style templates (T1, T2, T3, T5), <=400 for T4 (cover letter).
- Include 1-2 portfolio projects when relevant (cite JARVIS most often).
- Reference one specific thing from their post/bio (the {{specific_thing}} placeholder).
- Do NOT echo the prompt or template structure back. Just output the email.
- CRITICAL: If the job mentioned is Sales, HR, BPO, Customer Support, Marketing, or NOT Software Engineering / Data / AI, output EXACTLY: UNRELATED_ROLE"""


def generate_cold_email(
    post_text: str,
    recruiter_name: str,
    bio_text: str = "",
    template_id: str = "T2",
    tier: str = "T3",
):
    """Generate a personalized cold email through JARVIS policy.

    Args:
        post_text: The LinkedIn post content (job description / recruiter's post).
        recruiter_name: Recruiter's full name.
        bio_text: Recruiter's bio from profile scrape (optional).
        template_id: One of T1, T2, T3, T4, T5. Defaults to T2 (LinkedIn DM).
        tier: T1 (founder), T2 (hiring manager), T3 (recruiter reply). Used for metrics only.

    Returns:
        Tuple of (subject, body), or (None, None) on failure.
    """
    chain = _strip_cloud_entries(_resolve_chain())
    if not chain:
        print("  ❌ NO models left in chain (all were 'cloud' and JARVIS_ALLOW_CLOUD is unset).")
        return None, None

    # Load portfolio
    portfolio_text = ""
    portfolio_path = Path(__file__).parent / "portfolio.json"
    if portfolio_path.exists():
        try:
            with open(portfolio_path, "r", encoding="utf-8") as f:
                projects = json.load(f)
                for p in projects:
                    portfolio_text += f"- {p.get('project_name', 'Project')}: {p.get('description', '')} (Stack: {p.get('tech_stack', '')})\n"
        except Exception as e:
            print(f"  ⚠ Failed to load portfolio.json: {e}")

    prompt = _build_prompt(recruiter_name, post_text, bio_text, portfolio_text, template_id)

    print(
        f"  🤖 generating email for {recruiter_name!r} "
        f"(template={template_id}, tier={tier}; chain: {' → '.join(chain)})"
    )

    for model in chain:
        response = _try_model_via_policy(model, prompt, recruiter_name)
        if response:
            if "UNRELATED_ROLE" in response:
                print(f"  ↪ AI rejected {recruiter_name}'s post as unrelated non-tech role.")
                return None, None

            lines = response.strip().split("\n")
            subject = f"Application - {recruiter_name}"
            body = response

            if lines[0].lower().startswith("subject:"):
                subject = lines[0][8:].strip()
                body = "\n".join(lines[1:]).strip()

            return subject, body

    print(f"  ❌ ALL models failed for {recruiter_name!r}. Audit-logged in ~/.jarvis/audit.log.")
    return None, None
