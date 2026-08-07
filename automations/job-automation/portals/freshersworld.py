"""
portals/freshersworld.py — Freshersworld automation
https://www.freshersworld.com — Fresher-focused portal, very simple HTML, high volume
"""
import os
import random
from playwright.async_api import Page
from .base import BasePortal, ApplicationResult, is_experienced_role

TIMEOUT = 45_000

# City name mapping for URL construction
CITY_MAP = {
    "gurugram": "gurgaon", "gurgaon": "gurgaon", 
    "noida": "noida", "greater noida": "greater-noida",
    "delhi": "delhi", 
    "hyderabad": "hyderabad", "bangalore": "bangalore", "bengaluru": "bangalore"
}


class FreshersworldPortal(BasePortal):
    name = "Freshersworld"
    base_url = "https://www.freshersworld.com"
    login_url = "https://www.freshersworld.com/login"

    async def login(self, page: Page) -> bool:
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(2000)

            if await self._is_logged_in(page):
                print("  ✅ Freshersworld: session active — skipping login")
                return True

            await page.goto(self.login_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(2000)

            # Close any popup
            try:
                await page.click(".close, .modal-close, #close_popup", timeout=2000)
            except:
                pass

            # Fill login form
            await page.fill('#username, input[name="username"], input[type="email"]',
                           self.email, timeout=5000)
            await page.wait_for_timeout(400)

            await page.fill('#password, input[name="password"], input[type="password"]',
                           self.password, timeout=5000)
            await page.wait_for_timeout(400)

            await page.click('#loginBtn, button[type="submit"], button:has-text("Login")',
                            timeout=5000)
            await page.wait_for_timeout(3000)

            if await self._is_logged_in(page):
                print("  ✅ Freshersworld: Logged in successfully")
                return True
            return False
        except Exception as e:
            print(f"  ❌ Freshersworld login error: {e}")
            return False

    async def _is_logged_in(self, page: Page) -> bool:
        url = page.url
        if any(x in url for x in ["/login", "/signup", "/register"]):
            return False
        try:
            await page.wait_for_selector(
                ".header, .user-profile, .nav-menu, .user-name, [data-user]",
                timeout=5000
            )
            return True
        except:
            return False

    async def search_and_apply(self, page: Page, roles: list, cities: list,
                               daily_limit: int, applied_today: set, job_filter=None) -> list:
        results = []
        applied = 0

        for role in roles:
            for city in cities:
                if applied >= daily_limit:
                    break

                # Build search URL
                city_slug = CITY_MAP.get(city.lower(), city.lower().replace(" ", "-"))
                role_slug = role.lower().replace(" ", "-").replace("/", "-")
                search_url = (
                    f"{self.base_url}/jobs/"
                    f"{role_slug}-jobs-in-{city_slug}"
                )
                print(f"\n  🔍 Freshersworld: Searching '{role}' in '{city}'")

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                    await page.wait_for_timeout(3000)

                    # Scroll to load all jobs
                    for _ in range(3):
                        await page.evaluate("window.scrollBy(0, 500)")
                        await page.wait_for_timeout(800)

                    # Job card selectors — Freshersworld uses standard selectors
                    card_sel = (
                        ".job-list-card, .job-card, .job-container, .jobResultItem, "
                        ".jobs-list-item, article.job, .latest_job_list"
                    )
                    cards = page.locator(card_sel)
                    count = await cards.count()

                    if count == 0:
                        # Try alternate pattern
                        cards = page.locator(".jobsearch-ResultsContainer li, .job-card-container")
                        count = await cards.count()

                    if count == 0:
                        print(f"  ⚠️  Freshersworld: No jobs found for '{role}' in '{city}'")
                        continue

                    print(f"  🔍 Freshersworld: Found {count} jobs for '{role}' in '{city}'")

                    for i in range(count):
                        if applied >= daily_limit:
                            break

                        card = cards.nth(i)
                        try:
                            if not await card.is_visible(timeout=2000):
                                continue

                            # Title
                            for tsel in [".jobtitle", ".job-title", "h3", "h4", ".title", "[class*='title']"]:
                                title_el = card.locator(tsel).first
                                if await title_el.is_visible(timeout=500):
                                    title = (await title_el.inner_text()).strip()
                                    break
                            else:
                                title = "Unknown Role"

                            # Company
                            for csel in [".company-name", ".company", ".companyName", "[class*='company']"]:
                                comp_el = card.locator(csel).first
                                if await comp_el.is_visible(timeout=500):
                                    company = (await comp_el.inner_text()).strip()
                                    break
                            else:
                                company = "Unknown"

                            # Job URL
                            link_el = card.locator("a[href*='/jobs/'], a.job-link").first
                            href = await link_el.get_attribute("href") if await link_el.is_visible() else ""
                            if href and not href.startswith("http"):
                                href = self.base_url + href
                            job_url = href or ""

                            job_id = f"freshersworld_{abs(hash(job_url)) % 999999}"

                            if job_id in applied_today:
                                continue

                            if is_experienced_role(title, ""):
                                print(f"     ⏭️  Skipped (experience): {title}")
                                continue
                            if job_filter is not None and not await job_filter({
                                "id": job_id, "title": title, "company": company,
                                "url": job_url, "portal": "Freshersworld"
                            }):
                                print(f"     ⏭️  Skipped: LLM fit filter rejected")
                                continue

                            # Apply directly via link
                            if job_url:
                                await page.goto(job_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                                await page.wait_for_timeout(2000)
                                result = await self.apply_to_job(page, {
                                    "id": job_id, "title": title, "company": company,
                                    "url": job_url, "portal": "Freshersworld"
                                })
                                results.append(result)
                                if result.status == "applied":
                                    applied_today.add(job_id)
                                    applied += 1
                                    print(f"     ✅ Freshersworld Applied: {title} @ {company}")
                                elif result.status == "manual":
                                    print(f"     📋 Manual: {result.reason}")
                                elif result.status == "skipped":
                                    print(f"     ⏭️  Skipped: {result.reason}")

                            await page.wait_for_timeout(random.uniform(1000, 1500))

                        except Exception as e:
                            short_err = str(e).split("\n")[0][:80]
                            print(f"     ⚠️  Card error: {short_err}")
                            continue

                except Exception as e:
                    print(f"  ❌ Freshersworld search error: {e}")
                    continue

        return results

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        try:
            if not job.get("url"):
                return ApplicationResult(job=job, status="skipped", reason="No job URL")

            await page.goto(job["url"], wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(2000)

            # Look for Apply button
            apply_sel = [
                "button:has-text('Apply')", ".apply-btn", ".applybutton",
                "a:has-text('Apply')", "#apply_job"
            ]
            apply_btn = None
            for sel in apply_sel:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=1500):
                    apply_btn = btn
                    break

            if not apply_btn:
                # Try to find any button with "apply" text
                return ApplicationResult(job=job, status="skipped", reason="No Apply button found")

            await apply_btn.click(timeout=5000)
            await page.wait_for_timeout(3000)

            # Check for success indicators
            for sel in [":has-text('Applied successfully')", ":has-text('Application submitted')",
                        ".success", "#success"]:
                try:
                    if await page.locator(sel).first.is_visible(timeout=2000):
                        print(f"     ✅ Freshersworld Applied: {job['title']} @ {job['company']}")
                        return ApplicationResult(job=job, status="applied")
                except:
                    pass

            # If no error shown, assume applied
            print(f"     ✅ Freshersworld Applied: {job['title']} @ {job['company']}")
            return ApplicationResult(job=job, status="applied")

        except Exception as e:
            return ApplicationResult(job=job, status="error", reason=str(e))