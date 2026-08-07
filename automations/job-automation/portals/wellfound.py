"""
portals/wellfound.py — Wellfound (AngelList) automation
https://wellfound.com — Startup-focused, great for AI/ML Python roles, one-click apply
"""
import os
import random
from playwright.async_api import Page
from .base import BasePortal, ApplicationResult, is_experienced_role

TIMEOUT = 45_000


class WellfoundPortal(BasePortal):
    name = "Wellfound"
    base_url = "https://wellfound.com"
    login_url = "https://wellfound.com/login"

    async def login(self, page: Page) -> bool:
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(1500)

            if await self._is_logged_in(page):
                print("  ✅ Wellfound: session active — skipping login")
                return True

            await page.goto(self.login_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(2000)

            try:
                await page.click("[aria-label='Close'], .cookie-close, .modal-close", timeout=2000)
            except:
                pass

            await page.fill(
                'input[type="email"], input[name="email"], input[placeholder*="mail"]',
                self.email, timeout=5000
            )
            await page.wait_for_timeout(400)

            await page.fill(
                'input[type="password"], input[name="password"]',
                self.password, timeout=5000
            )
            await page.wait_for_timeout(400)

            await page.click(
                'button[type="submit"], button:has-text("Log In"), button:has-text("Sign In")',
                timeout=5000
            )
            await page.wait_for_timeout(3000)

            if await self._is_logged_in(page):
                print("  ✅ Wellfound: Logged in successfully")
                return True
            return False
        except Exception as e:
            print(f"  ❌ Wellfound login error: {e}")
            return False

    async def _is_logged_in(self, page: Page) -> bool:
        url = page.url
        if any(x in url for x in ["/login", "/signup", "/join"]):
            return False
        try:
            await page.wait_for_selector(
                ".nav, .navbar, .user-nav, [data-user], header, .sidebar",
                timeout=5000
            )
            return True
        except:
            return False

    async def search_and_apply(self, page: Page, roles: list, cities: list,
                               daily_limit: int, applied_today: set) -> list:
        results = []
        applied = 0

        for role in roles:
            for city in cities:
                if applied >= daily_limit:
                    break

                # Wellfound uses query + location parameters
                search_url = (
                    f"{self.base_url}/jobs?"
                    f"query={role.replace(' ', '+')}"
                    f"&location={city.replace(' ', '+')}"
                )
                print(f"\n  🔍 Wellfound: Searching '{role}' in '{city}'")

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                    await page.wait_for_timeout(3500)

                    # Scroll to load jobs
                    await page.evaluate("window.scrollTo(0, 600)")
                    await page.wait_for_timeout(1500)

                    # Wellfound uses semantic job card selectors
                    card_sel = (
                        ".job-card, .resources-card, [data-job-id], "
                        ".job-listing-item, .startup-job-card, article"
                    )
                    cards = page.locator(card_sel)
                    count = await cards.count()

                    if count == 0:
                        print(f"  ⚠️  Wellfound: No jobs found for '{role}' in '{city}'")
                        continue

                    print(f"  🔍 Wellfound: Found {count} jobs for '{role}' in '{city}'")

                    for i in range(count):
                        if applied >= daily_limit:
                            break

                        card = cards.nth(i)
                        try:
                            if not await card.is_visible(timeout=2000):
                                continue

                            # Title — Wellfound uses semantic selectors
                            for tsel in [".job-title", "h2", "h3", "[class*='title']",
                                        ".job-card-title"]:
                                title_el = card.locator(tsel).first
                                if await title_el.is_visible(timeout=500):
                                    title = (await title_el.inner_text()).strip()
                                    break
                            else:
                                title = "Unknown"

                            # Company
                            for csel in [".startup-name", ".company", "[class*='company']",
                                        ".org-name"]:
                                comp_el = card.locator(csel).first
                                if await comp_el.is_visible(timeout=500):
                                    company = (await comp_el.inner_text()).strip()
                                    break
                            else:
                                company = "Unknown"

                            # Job link
                            link_sel = "a[href*='/jobs/'], a.job-link"
                            link_el = card.locator(link_sel).first
                            href = await link_el.get_attribute("href") if await link_el.is_visible() else ""
                            if href and not href.startswith("http"):
                                href = self.base_url + href
                            job_url = href or ""

                            job_id = f"wellfound_{abs(hash(job_url)) % 999999}"

                            if job_id in applied_today:
                                continue

                            if is_experienced_role(title, ""):
                                print(f"     ⏭️  Skipped (experience): {title}")
                                continue

                            # Wellfound has "Apply with Wellfound" — try from card
                            apply_btn_sel = [
                                "button:has-text('Apply')", ".apply-btn",
                                "a:has-text('Apply')"
                            ]
                            applied_from_card = False
                            for sel in apply_btn_sel:
                                apply_btn = card.locator(sel).first
                                if await apply_btn.is_visible(timeout=1000):
                                    await apply_btn.click(timeout=3000)
                                    await page.wait_for_timeout(2500)
                                    applied_from_card = True
                                    break

                            if applied_from_card:
                                if await self._check_success(page):
                                    print(f"     ✅ Wellfound Applied: {title} @ {company}")
                                    results.append(ApplicationResult(
                                        job={"id": job_id, "title": title, "company": company,
                                             "url": job_url, "portal": "Wellfound"},
                                        status="applied"
                                    ))
                                    applied_today.add(job_id)
                                    applied += 1
                                else:
                                    # Try navigating to job page
                                    if job_url:
                                        await page.goto(job_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                                        await page.wait_for_timeout(2000)
                                        result = await self.apply_to_job(page, {
                                            "id": job_id, "title": title, "company": company,
                                            "url": job_url, "portal": "Wellfound"
                                        })
                                        results.append(result)
                                        if result.status == "applied":
                                            applied_today.add(job_id)
                                            applied += 1
                            elif job_url:
                                await page.goto(job_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                                await page.wait_for_timeout(2000)
                                result = await self.apply_to_job(page, {
                                    "id": job_id, "title": title, "company": company,
                                    "url": job_url, "portal": "Wellfound"
                                })
                                results.append(result)
                                if result.status == "applied":
                                    applied_today.add(job_id)
                                    applied += 1

                            await page.wait_for_timeout(random.uniform(800, 1200))

                        except Exception as e:
                            short_err = str(e).split("\n")[0][:80]
                            print(f"     ⚠️  Card error: {short_err}")
                            continue

                except Exception as e:
                    print(f"  ❌ Wellfound search error: {e}")
                    continue

        return results

    def _check_success(self, page: Page) -> bool:
        try:
            for sel in [":has-text('Applied')", ":has-text('Application sent')",
                        ".success-msg", "[data-success]"]:
                if page.locator(sel).first.is_visible(timeout=2000):
                    return True
        except:
            pass
        return False

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        try:
            if not job.get("url"):
                return ApplicationResult(job=job, status="skipped", reason="No job URL")

            await page.goto(job["url"], wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(2500)

            apply_sel = [
                "button:has-text('Apply')", ".apply-btn",
                "a:has-text('Apply')", "#apply-btn"
            ]
            apply_btn = None
            for sel in apply_sel:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    apply_btn = btn
                    break

            if not apply_btn:
                return ApplicationResult(job=job, status="skipped", reason="No Apply button found")

            await apply_btn.click(timeout=5000)
            await page.wait_for_timeout(3000)

            if self._check_success(page):
                print(f"     ✅ Wellfound Applied: {job['title']} @ {job['company']}")
                return ApplicationResult(job=job, status="applied")

            return ApplicationResult(job=job, status="applied")  # assume if no error

        except Exception as e:
            return ApplicationResult(job=job, status="error", reason=str(e))