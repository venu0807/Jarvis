"""
portals/base.py — Base class and shared types for all portal automations
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from playwright.async_api import Page

NAME      = os.getenv("USER_FULL_NAME", "User Name")
EMAIL     = os.getenv("GMAIL_ADDRESS", "user@example.com")
PHONE_RAW = os.getenv("USER_PHONE", "+910000000000")
PHONE_DIGITS = PHONE_RAW.replace("+91", "").replace("+", "").strip()


@dataclass
class ApplicationResult:
    job: dict
    status: str          # "applied" | "manual" | "skipped" | "error"
    reason: str = ""
    resume_pdf: str = "" # path to tailored resume PDF (filled after tailoring)


def is_experienced_role(title: str, description: str = "") -> bool:
    """
    Returns True if the job strictly requires experience and is NOT a fresher/intern role.
    """
    text = f"{title} {description}".lower()
    
    if any(x in title.lower() for x in ["intern", "fresher", "trainee", "junior", "entry level"]):
        return False
        
    # Catch senior/management/mid-level titles
    if any(x in title.lower() for x in ["senior", "sr.", "sr ", "lead", "staff", "principal", "manager", "director", "head", "architect", "mid-level", "experienced", "vp"]):
        return True
        
    import re
    # Reject if it explicitly asks for 1 or more years of experience
    exp_matches = re.findall(r'([0-9]+)\s*\+\s*(?:years?|yrs?)(?:\s+of)?\s+exp', text)
    for match in exp_matches:
        if int(match) >= 1:  # Skip if 1+ years explicitly required
            return True
            
    exp_matches_range = re.findall(r'([0-9]+)\s*(?:to|-)\s*([0-9]+)\s*(?:years?|yrs?)(?:\s+of)?\s+exp', text)
    for match in exp_matches_range:
        if int(match[0]) >= 1:  # Skip if minimum experience is 1+ years
            return True
            
    # Check for raw "X years experience" without the "+" or "to".
    # Lookbehind blocks the upper bound of a range ("0-1 years", "0 to 1 years")
    # from being misread as a standalone "1 years" requirement.
    raw_exp = re.findall(r'(?<![0-9-])(?<!to )([0-9]+)\s*(?:years?|yrs?)(?:\s+of)?(?:\s+(?:work|professional))?\s+experience', text)
    for match in raw_exp:
        if int(match) >= 1:
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
                        if NAME and NAME != "User Name":
                            await el.fill(NAME)
                        else:
                            await el.fill("User Name")
                    break
            except:
                continue
        for ln_sel in ["input[name='lastName']", "input[id*='lastName']", "input[placeholder*='ast']"]:
            try:
                el = page.locator(ln_sel).first
                if await el.is_visible(timeout=400):
                    if not await el.input_value():
                        await el.fill("Palugulla")
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
