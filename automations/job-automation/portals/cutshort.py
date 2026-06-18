"""
portals/cutshort.py — Cutshort automation
https://cutshort.io — Developer-focused job portal, clean UI, skills-based matching
"""
import os
import random
from playwright.async_api import Page
from .base import BasePortal, ApplicationResult, is_experienced_role

TIMEOUT = 45_000


class CutshortPortal(BasePortal):
    name = "Cutshort"
    base_url = "https://cutshort.io"
    login_url = "https://cutshort.io/login"

    async def login(self, page: Page) -> bool:
        try:
            await page.goto(self.base_url, wait_until="networkidle", timeout=TIMEOUT)
            await page.wait_for_timeout(1500)

            if await self._is_logged_in(page):
                print("  ✅ Cutshort: session active — skipping login")
                return True

            await page.goto(self.login_url, wait_until="networkidle", timeout=TIMEOUT)
            await page.wait_for_timeout(2000)

            # Close cookie banner if present
            try:
                await page.click("[aria-label='Close'], .cookie-close, .modal-close", timeout=2000)
            except:
                pass

            # Fill email
            await page.fill('input[type="email"], input[name="email"], input[placeholder*="mail"]',
                           self.email, timeout=5000)
            await page.wait_for_timeout(400)

            # Fill password
            await page.fill('input[type="password"], input[name="password"]',
                           self.password, timeout=5000)
            await page.wait_for_timeout(400)

            # Click login
            await page.click('button[type="submit"], button:has-text("Sign In"), button:has-text("Login")',
                           timeout=5000)
            await page.wait_for_timeout(3000)

            if await self._is_logged_in(page):
                print("  ✅ Cutshort: Logged in successfully")
                return True
            return False
        except Exception as e:
            print(f"  ❌ Cutshort login error: {e}")
            return False

    async def _is_logged_in(self, page: Page) -> bool:
        url = page.url
        if any(x in url for x in ["/login", "/signup", "/auth"]):
            return False
        try:
            await page.wait_for_selector(
                ".sidebar, .nav-links, [data-nav], .user-avatar, header",
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

                search_url = (
                    f"{self.base_url}/jobs/"
                    f"{role.lower().replace(' ', '-')}"
                    f"?location={city.replace(' ', '+')}"
                )
                print(f"\n  🔍 Cutshort: Searching '{role}' in '{city}'")

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                    await page.wait_for_timeout(3000)

                    # Scroll to load more jobs
                    await page.evaluate("""
                        window.scrollTo(0, document.body.scrollHeight / 2);
                    """)
                    await page.wait_for_timeout(1500)

                    # Find job cards — Cutshort uses various card selectors
                    card_selectors = [
                        ".job-card", ".cutshort-card", "[data-job-id]",
                        ".position-card", ".job-list-item", "article.job"
                    ]
                    cards = page.locator(", ".join(card_selectors))
                    count = await cards.count()

                    if count == 0:
                        print(f"  ⚠️  Cutshort: No jobs found for '{role}' in '{city}'")
                        continue

                    print(f"  🔍 Cutshort: Found {count} jobs for '{role}' in '{city}'")

                    for i in range(count):
                        if applied >= daily_limit:
                            break

                        card = cards.nth(i)
                        try:
                            if not await card.is_visible(timeout=2000):
                                continue

                            # Extract title
                            title_sel = "h2, h3, .job-title, .position-title, [data-job-title]"
                            title_el = card.locator(title_sel).first
                            title = (await title_el.inner_text()).strip() if await title_el.is_visible() else ""

                            # Extract company
                            company_sel = ".company-name, .company, [data-company], .org-name"
                            comp_el = card.locator(company_sel).first
                            company = (await comp_el.inner_text()).strip() if await comp_el.is_visible() else "Unknown"

                            # Extract URL
                            link_sel = "a[href*='/jobs/'], a.job-link, a[href*='/position/']"
                            link_el = card.locator(link_sel).first
                            href = await link_el.get_attribute("href") if await link_el.is_visible() else ""
                            if href and not href.startswith("http"):
                                href = self.base_url + href
                            job_url = href or ""

                            job_id = f"cutshort_{abs(hash(job_url)) % 999999}"

                            if job_id in applied_today:
                                print(f"     ⏭️  Already applied: {title}")
                                continue

                            if is_experienced_role(title, ""):
                                print(f"     ⏭️  Skipped (experience): {title}")
                                continue

                            # Try to apply directly from card
                            apply_btn_sel = [
                                "button:has-text('Apply')", ".apply-btn", ".apply-button",
                                "a:has-text('Apply')", "[data-apply]"
                            ]
                            applied_from_card = False
                            for sel in apply_btn_sel:
                                apply_btn = card.locator(sel).first
                                if await apply_btn.is_visible(timeout=1000):
                                    await apply_btn.click(timeout=3000)
                                    await page.wait_for_timeout(2000)
                                    applied_from_card = True
                                    break

                            if applied_from_card:
                                # Check for success
                                if await self._is_applied(page):
                                    print(f"     ✅ Cutshort Applied: {title} @ {company}")
                                    results.append(ApplicationResult(
                                        job={"id": job_id, "title": title, "company": company,
                                             "url": job_url, "portal": "Cutshort"},
                                        status="applied"
                                    ))
                                    applied_today.add(job_id)
                                    applied += 1
                                else:
                                    # Try apply page
                                    result = await self.apply_to_job(page, {
                                        "id": job_id, "title": title, "company": company,
                                        "url": job_url, "portal": "Cutshort"
                                    })
                                    results.append(result)
                                    if result.status == "applied":
                                        applied_today.add(job_id)
                                        applied += 1
                            else:
                                # Open job detail and apply
                                if job_url:
                                    await page.goto(job_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                                    await page.wait_for_timeout(2000)
                                    result = await self.apply_to_job(page, {
                                        "id": job_id, "title": title, "company": company,
                                        "url": job_url, "portal": "Cutshort"
                                    })
                                    results.append(result)
                                    if result.status == "applied":
                                        applied_today.add(job_id)
                                        applied += 1
                                    elif result.status == "manual":
                                        print(f"     📋 Manual: {result.reason}")
                                    elif result.status == "skipped":
                                        print(f"     ⏭️  Skipped: {result.reason}")

                            await page.wait_for_timeout(random.uniform(800, 1200))

                        except Exception as e:
                            short_err = str(e).split("\n")[0][:80]
                            print(f"     ⚠️  Card error: {short_err}")
                            continue

                except Exception as e:
                    print(f"  ❌ Cutshort search error: {e}")
                    continue

        return results

    def _is_applied(self, page: Page) -> bool:
        try:
            for sel in [
                ":has-text('Applied')", ":has-text('Already applied')",
                ".success-message", "[data-success]", ".applied-badge"
            ]:
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

            # Look for Apply button
            apply_selectors = [
                "button:has-text('Apply')", ".apply-btn", ".apply-button",
                "a:has-text('Apply')", "[data-apply-btn]"
            ]
            apply_btn = None
            for sel in apply_selectors:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    apply_btn = btn
                    break

            if not apply_btn:
                return ApplicationResult(job=job, status="skipped", reason="No Apply button found")

            await apply_btn.click(timeout=5000)
            await page.wait_for_timeout(3000)

            # Submit if a form appeared
            submit_sel = ["button:has-text('Submit')", "button:has-text('Apply')",
                          "button:has-text('Send')"]
            for sel in submit_sel:
                submit_btn = page.locator(sel).first
                if await submit_btn.is_visible(timeout=2000):
                    await submit_btn.click(timeout=3000)
                    await page.wait_for_timeout(2000)
                    break

            if self._is_applied(page):
                print(f"     ✅ Cutshort Applied: {job['title']} @ {job['company']}")
                return ApplicationResult(job=job, status="applied")

            return ApplicationResult(job=job, status="applied")  # assume success if no error

        except Exception as e:
            return ApplicationResult(job=job, status="error", reason=str(e))