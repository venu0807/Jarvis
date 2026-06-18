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

Active (8):
  - NaukriPortal, FounditPortal — strong B2B engines
  - IndeedPortal, InternshalaPortal — keep + tune
  - CutshortPortal, FreshersworldPortal, WellfoundPortal — niche but
    occasionally surface fresher roles
  - CareerPagePortal — aggregator JSON APIs (Greenhouse/Lever/Ashby/Recruitee)
    + custom POST apply endpoints. Real auto-apply via `career_pages_apply.py`.

Note: cut portal source kept in `.cut-2026-06-15/` for one cycle. After you
verify everything works without them, run:
    python scripts/apply_portal_cuts.py --finalize --i-know-what-im-doing
That removes the staging directory and the script itself.
"""

from .naukri import NaukriPortal
from .internshala import IntersahalaPortal
from .indeed import IndeedPortal
from .foundit import FounditPortal
from .cutshort import CutshortPortal
from .freshersworld import FreshersworldPortal
from .wellfound import WellfoundPortal
from .career_pages import CareerPagePortal
from .workday import WorkdayPortal

__all__ = [
    "NaukriPortal",
    "IntersahalaPortal",
    "IndeedPortal",
    "FounditPortal",
    "CutshortPortal",
    "FreshersworldPortal",
    "WellfoundPortal",
    "CareerPagePortal",
    "WorkdayPortal",
]
