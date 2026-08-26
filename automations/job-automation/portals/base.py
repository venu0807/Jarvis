"""
portals/base.py — Base class and shared types for all portal automations
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from playwright.async_api import Page

NAME      = os.getenv("USER_FULL_NAME", "User Name")
EMAIL     = os.getenv("GMAIL_ADDRESS", "user@example.com")
PHONE_RAW = os.getenv("USER_PHONE", "+910000000000")
PHONE_DIGITS = PHONE_RAW.replace("+91", "").replace("+", "").strip()

# Derive first/last name from USER_FULL_NAME ("First Last") instead of
# hardcoding. USER_LAST_NAME overrides when the full name is ambiguous.
_NAME_PARTS = NAME.split(maxsplit=1)
FIRST_NAME  = _NAME_PARTS[0] if _NAME_PARTS else ""
LAST_NAME   = os.getenv("USER_LAST_NAME", "") or (_NAME_PARTS[1] if len(_NAME_PARTS) > 1 else "")


@dataclass
class ApplicationResult:
    job: dict
    status: str          # "applied" | "manual" | "skipped" | "error"
    reason: str = ""
    resume_pdf: str = "" # path to tailored resume PDF (filled after tailoring)


def is_experienced_role(title: str, description: str = "") -> bool:
    """
    Returns True if the job strictly requires experience (>1-2 years) and is NOT a fresher/intern role.
    """
    t_lower = (title or "").lower()
    text = f"{title} {description}".lower()
    
    # Priority 1: Clear fresher/intern indicators in title ALWAYS pass
    if any(x in t_lower for x in ["intern", "fresher", "trainee", "graduate trainee", "campus", "entry level", "entry-level"]):
        return False
        
    # Priority 2: Senior, Lead, Management keywords in title ALWAYS fail
    senior_keywords = [
        "senior", "sr.", "sr ", "lead", "staff", "principal", "manager", "director",
        "head", "architect", "mid-level", "mid level", "experienced", "specialist",
        "consultant", "vp", "avp", "tech lead", "team lead", "sde 2", "sde ii",
        "sde 3", "sde iii", "sde-2", "sde-ii", "sde-3", "sde-iii", "level 2", "level 3"
    ]
    if any(x in t_lower for x in senior_keywords):
        return True
        
    # Priority 3: Experience ranges (e.g., "2-5 Yrs", "3 - 6 Years", "2 to 4 years", "1 - 3 Yrs")
    range_matches = re.findall(r'([0-9]+)\s*(?:to|-)\s*([0-9]+)\s*(?:years?|yrs?|yr)', text)
    for min_yr, max_yr in range_matches:
        min_val = int(min_yr)
        max_val = int(max_yr)
        # If minimum experience is 2+ years, skip
        if min_val >= 2:
            return True
        # If minimum is 1 and max is 3+ (e.g. 1-4 years, 1-5 years), skip
        if min_val == 1 and max_val >= 3:
            return True

    # Priority 4: Plus experience (e.g., "2+ years", "3+ Yrs", "2+ yrs exp")
    plus_matches = re.findall(r'([0-9]+)\s*\+\s*(?:years?|yrs?|yr)', text)
    for val in plus_matches:
        if int(val) >= 2:
            return True

    # Priority 5: Explicit "Exp: X years" or "Experience: X Yrs"
    labeled_matches = re.findall(r'(?:exp|experience)\s*[:\-]?\s*([0-9]+)\s*(?:to|-)?\s*([0-9]+)?\s*(?:years?|yrs?|yr)?', text)
    for match in labeled_matches:
        if match[0] and int(match[0]) >= 2:
            return True

    # Priority 6: Raw standalone "X years of experience" / "X yrs experience"
    raw_matches = re.findall(r'(?<![0-9-])(?<!to )([0-9]+)\s*(?:years?|yrs?|yr)(?:\s+of)?(?:\s+(?:work|professional|relevant))?\s+experience', text)
    for val in raw_matches:
        if int(val) >= 2:
            return True

    return False


class BasePortal:
    name: str = ""
    base_url: str = ""
    login_url: str = ""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password

    async def login(self, page: Page) -> bool:
        raise NotImplementedError

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        raise NotImplementedError

    async def extract_similar_jobs(self, page: Page, roles: list, city: str = "") -> list:
        """Extract similar jobs from the page, returning a list of job dicts."""
        return []

    async def fill_external_form(self, page: Page) -> bool:
        """
        Fill a generic third-party application form (Name / Email / Phone / checkbox).
        Returns True if a submit button was found and clicked.
        Works on any page — used when Apply redirects to an external URL.
        """
        await page.wait_for_timeout(1500)

        # ── Name ──────────────────────────────────────────────────────────────
        for sel in [
            "input[placeholder='Name']", "input[placeholder='Full Name']",
            "input[placeholder='Your Name']", "input[name='name']",
            "input[id*='name']", "input[aria-label*='name' i]",
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=600):
                    if not await el.input_value():
                        await el.fill(NAME)
                    break
            except:
                continue

        # ── First / Last name ─────────────────────────────────────────────────
        for fn_sel in ["input[name='firstName']", "input[id*='firstName']", "input[placeholder*='irst']"]:
            try:
                el = page.locator(fn_sel).first
                if await el.is_visible(timeout=400):
                    if not await el.input_value():
                        await el.fill(FIRST_NAME)
                    break
            except:
                continue
        for ln_sel in ["input[name='lastName']", "input[id*='lastName']", "input[placeholder*='ast']"]:
            try:
                el = page.locator(ln_sel).first
                if await el.is_visible(timeout=400):
                    if not await el.input_value():
                        await el.fill(LAST_NAME)
                    break
            except:
                continue

        # ── Email ─────────────────────────────────────────────────────────────
        for sel in [
            "input[type='email']", "input[placeholder='Email']",
            "input[placeholder*='mail' i]", "input[name='email']", "input[id*='email']",
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=600):
                    if not await el.input_value():
                        await el.fill(EMAIL)
                    break
            except:
                continue

        # ── Phone ─────────────────────────────────────────────────────────────
        for sel in [
            "input[type='tel']", "input[placeholder='Phone number']",
            "input[placeholder='Phone Number']", "input[placeholder*='hone' i]",
            "input[name='phone']", "input[id*='phone']",
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=600):
                    if not await el.input_value():
                        await el.fill(PHONE_DIGITS)
                    break
            except:
                continue

        # ── Checkboxes (verify / agree) ───────────────────────────────────────
        try:
            cbs = page.locator("input[type='checkbox']")
            cnt = await cbs.count()
            for i in range(cnt):
                cb = cbs.nth(i)
                if await cb.is_visible(timeout=400) and not await cb.is_checked():
                    await cb.click()
                    await page.wait_for_timeout(200)
        except:
            pass

        await page.wait_for_timeout(800)

        # ── Submit ────────────────────────────────────────────────────────────
        for sub_sel in [
            "button:has-text('Submit Application')",
            "button:has-text('Submit')",
            "input[type='submit']",
            "button[type='submit']",
            "button:has-text('Apply')",
            "button:has-text('Send')",
        ]:
            try:
                btn = page.locator(sub_sel).first
                if await btn.is_visible(timeout=1000):
                    await btn.click(timeout=5000)
                    await page.wait_for_timeout(2000)
                    return True
            except:
                continue

        return False  # No submit button found
