"""portals/profile.py — single source of truth for user profile + resume path.

Used to be hand-rolled in three divergent places:
  - career_pages_apply._load_profile()
  - workday._load_profile_dict()
  - auto_applier.CREDS (different shape again)
One parser + one resume-PDF lookup here; the portal modules import it.
"""
import os
from pathlib import Path
from typing import Optional

ENV_PATH = Path(__file__).parent.parent / ".env"


def _read_env() -> dict:
    """Parse the project .env into a plain dict (no python-dotenv dependency
    so portal modules can import this in isolation)."""
    out = {}
    if not ENV_PATH.exists():
        return out
    for raw in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k] = v.strip().strip('"').strip("'")
    return out


_ENV = _read_env()


def load_profile() -> dict:
    """Contact info used to fill application forms. Keys consumed by the
    apply modules: first_name, last_name, email, phone, linkedin, resume_pdf."""
    full = _ENV.get("USER_FULL_NAME", "")
    parts = full.split(maxsplit=1)
    # USER_LAST_NAME overrides when the full name is ambiguous ("First Last").
    last = _ENV.get("USER_LAST_NAME") or (parts[1] if len(parts) > 1 else "")
    return {
        "first_name": parts[0] if parts else "",
        "last_name":  last,
        "email":      _ENV.get("GMAIL_ADDRESS") or _ENV.get("USER_EMAIL", ""),
        "phone":      _ENV.get("USER_PHONE", ""),
        "linkedin":   _ENV.get("USER_LINKEDIN_URL", ""),
        "resume_pdf": _ENV.get("RESUME_PDF_PATH", ""),
    }


_PROFILE = load_profile()


def resolve_resume_path() -> Optional[str]:
    """Locate the resume PDF: env override → home ~/V/<name>.pdf.

    Per-company resume tailoring was removed 2026-08-11; a single neutral
    base resume is used for every application. Set RESUME_PDF_PATH in .env
    to point at your base resume.
    """
    explicit = _PROFILE.get("resume_pdf") or os.environ.get("RESUME_PDF_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    default = Path(os.path.expanduser("~")) / "V" / "VenuGopalReddy-Palugulla-AI-Resume.pdf"
    if default.exists():
        return str(default)
    out_dir = Path(__file__).parent.parent / "output" / "resumes"
    if out_dir.exists():
        pdfs = sorted(out_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if pdfs:
            chosen = str(pdfs[0])
            print(f"  ⚠️  WARNING: using newest tailored resume for apply: {Path(chosen).name}\n"
                  f"     This may be tailored for a different company. Set RESUME_PDF_PATH in .env\n"
                  f"     to pin your neutral base resume.")
            return chosen
    return None
