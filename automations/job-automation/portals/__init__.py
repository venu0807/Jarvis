"""
portals/__init__.py — registry of active portal modules.

Cut list (2026-06-15, FINAL — kept here only for visibility; restoration via
`scripts/apply_portal_cuts.py --restore <name>`):
  - LinkedInPortal: 3.9% apply rate over 180 jobs — multi-step Easy Apply
    with text questions and external redirects is the bottleneck. Worth
    dropping. Use linkedin-outreach/ for cold-mail instead.
  - GlassdoorPortal: 0% apply rate over 30 jobs — Cloudflare/CAPTCHA blocks
    automation. Cookies degrade in days.
  - UnstopPortal:    11.1% apply rate over 18 jobs — too few jobs to be
    worth the headful-reauth maintenance.

Active (4, post 2026-08-11 cut):
  - NaukriPortal, FounditPortal — strong B2B engines
  - IndeedPortal, InternshalaPortal — keep + tune

Removed 2026-08-11: Cutshort, Freshersworld, Wellfound (re-login burden),
CareerPages aggregator, Workday — not worth maintenance for the apply yield.
"""

from .naukri import NaukriPortal
from .internshala import InternshalaPortal
from .indeed import IndeedPortal
from .foundit import FounditPortal

__all__ = [
    "NaukriPortal",
    "InternshalaPortal",
    "IndeedPortal",
    "FounditPortal",
]
