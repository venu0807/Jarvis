import hashlib
from playwright.async_api import Page

from .base import BasePortal, ApplicationResult, is_experienced_role

class FounditPortal(BasePortal):
    name = "foundit"
    base_url = "https://www.foundit.in"
    login_url = "https://www.foundit.in/rio/login"

    async def login(self, page: Page) -> bool:
        """
        Login to Foundit.
        """
        try:
            await page.goto(self.base_url, timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Check if logged in (look for profile icon or logged-in specific text)
            if await page.locator("div.header-profile-icon").count() > 0 or await page.locator("a[href*='dashboard']").count() > 0:
                print("  ✅ Foundit: session active — skipping login")
                return True

            print("  🔑 Foundit: logging in...")
            await page.goto(self.login_url)
            await page.wait_for_timeout(2000)

            # Fill email only if input exists
            email_input = page.locator("input[name='userName'], input[id='userName'], input[name='signInName'], input[id='signInName']")
            if await email_input.count() > 0 and await email_input.first.is_visible(timeout=3000):
                await email_input.first.fill(self.email)
                
                proceed_btn = page.locator("button:has-text('Next'), button:has-text('Proceed')")
                if await proceed_btn.count() > 0:
                    await proceed_btn.click()
                    await page.wait_for_timeout(2000)

                # Then enter password
                pass_input = page.locator("input[name='password'], input[id='password'], input[type='password']")
                if await pass_input.count() > 0:
                    await pass_input.first.fill(self.password)
                    await page.click("button[type='submit'], button:has-text('Login')")
            
            await page.wait_for_timeout(5000)
            
            if await page.locator("div.header-profile-icon").count() > 0 or await page.locator("a[href*='dashboard']").count() > 0:
                print("  ✅ Foundit: login successful")
                return True
            else:
                print("  ⚠️  Foundit: login might require CAPTCHA/OTP.")
                print("  ⏳ You have 60 seconds to manually enter the OTP or solve the CAPTCHA in the browser window...")
                await page.wait_for_timeout(60000)
                return await page.locator("div.header-profile-icon").count() > 0 or await page.locator("a[href*='dashboard']").count() > 0

        except Exception as e:
            print(f"  ❌ Foundit login error: {e}")
            return False

    async def search_and_apply(self, page: Page, roles: list, cities: list, daily_limit: int, applied_today: set) -> list:
        """
        Searches for jobs and applies to them.
        """
        results = []
        applied_count = 0
        
        for role in roles:
            for city in cities:
                if applied_count >= daily_limit:
                    break
                    
                print(f"\n  🔍 Foundit: Searching for '{role}' in '{city}'")
                try:
                    # Navigate to search URL
                    search_url = f"{self.base_url}/srp/results?query={role.replace(' ', '%20')}&locations={city.replace(' ', '%20')}"
                    await page.goto(search_url, timeout=60000)
                    await page.wait_for_timeout(4000)
                    
                    # Wait for job cards (live DOM uses srpResultCardContainer > cardContainer)
                    job_cards = page.locator("div.srpResultCardContainer div.cardContainer")
                    count = await job_cards.count()
                    if count == 0:
                        continue

                    for i in range(min(count, 15)): # Limit to 15 per search
                        if applied_count >= daily_limit:
                            break

                        card = job_cards.nth(i)

                        try:
                            title_el = card.locator("div.jobTitle, .jobTitle, h2.jobTitle").first
                            title = (await title_el.inner_text()).strip() if await title_el.count() > 0 else f"Job {i}"

                            company_el = card.locator("div.companyName p, .companyName").first
                            company = (await company_el.inner_text()).strip() if await company_el.count() > 0 else "Unknown"

                            # Foundit cards have no per-job URL in DOM — apply happens in-card.
                            # Use the search URL as the job URL for db records.
                            job_url = search_url
                        except:
                            continue

                        # Generate a deterministic ID based on the job URL or title/company
                        url_hash = hashlib.sha256(job_url.encode()).hexdigest()[:10]
                        job_id = f"fi_{url_hash}_{title}_{company}".replace(" ", "_").lower()
                        if job_id in applied_today:
                            continue

                        job = {
                            "id": job_id,
                            "title": title,
                            "company": company,
                            "location": city,
                            "url": job_url,
                            "portal": self.name,
                        }

                        if is_experienced_role(title, ""):
                            print(f"     ⏭️  Skipped: Requires experience (not fresher/intern)")
                            continue

                        # Apply flow: click the card to open the detail panel,
                        # then click #applyNowBtn inside #applyJobJD.
                        try:
                            await card.scroll_into_view_if_needed(timeout=3000)
                            await card.click()
                            await page.wait_for_timeout(4000)

                            panel = page.locator("#applyJobJD").first
                            apply_btn = page.locator("#applyNowBtn").first

                            if not await panel.is_visible(timeout=4000):
                                print(f"     ⚠️  Foundit: apply panel did not open")
                                results.append(ApplicationResult(job, "manual", "Apply panel did not open"))
                            elif not await apply_btn.is_visible(timeout=3000):
                                print(f"     ⚠️  Foundit: applyNowBtn missing")
                                results.append(ApplicationResult(job, "manual", "Apply Now button missing"))
                            else:
                                await apply_btn.click()
                                await page.wait_for_timeout(4000)

                                # Success check — handled in modal/snackbar post-click.
                                body_text = (await page.locator("body").inner_text()).lower()
                                success_markers = [
                                    "application sent",
                                    "successfully applied",
                                    "applied",
                                    "application submitted",
                                ]
                                already_markers = ["already applied", "already shortlisted"]

                                if any(m in body_text for m in already_markers):
                                    results.append(ApplicationResult(job, "skipped", "Already applied"))
                                elif any(m in body_text for m in success_markers):
                                    print(f"     ✅ Foundit Applied: {title} @ {company}")
                                    results.append(ApplicationResult(job, "applied"))
                                    applied_count += 1
                                    applied_today.add(job_id)
                                else:
                                    # No explicit success marker — assume applied (clicked the only CTA).
                                    print(f"     ✅ Foundit Applied (assumed): {title} @ {company}")
                                    results.append(ApplicationResult(job, "applied"))
                                    applied_count += 1
                                    applied_today.add(job_id)
                        except Exception as ce:
                            print(f"     ❌ Foundit apply error: {ce}")
                            results.append(ApplicationResult(job, "error", str(ce)))
                        finally:
                            # Always return to the search listing so the next card click is reliable.
                            try:
                                if page.url != search_url:
                                    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                                else:
                                    await page.go_back()
                                    await page.wait_for_timeout(2000)
                                await page.wait_for_timeout(2500)
                            except Exception:
                                pass
                                
                except Exception as e:
                    print(f"  ❌ Foundit search error [{role}/{city}]: {e}")
                    
        return results
