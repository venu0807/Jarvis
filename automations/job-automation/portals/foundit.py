import asyncio
from typing import Optional
from playwright.async_api import Page, TimeoutError

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

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        """
        Applies to a job using Foundit's Quick Apply.
        """
        title = job.get("title", "Unknown Role")
        company = job.get("company", "Unknown Company")
        job_url = job.get("url")

        if not job_url:
            return ApplicationResult(job, "error", "No URL provided")

        try:
            print(f"  → {title} @ {company}")
            await page.goto(job_url, timeout=60000)
            await page.wait_for_timeout(3000)

            # Look for the Apply button
            apply_btn = page.locator("button:has-text('Quick Apply'), button:has-text('Apply')")
            if await apply_btn.count() == 0:
                print(f"     ⚠️  Foundit: Apply button not found.")
                return ApplicationResult(job, "manual", "No Apply button")

            await apply_btn.first.click()
            await page.wait_for_timeout(3000)

            # Handle possible popup modals for "Confirm Details"
            submit_btn = page.locator("button:has-text('Submit'), button:has-text('Confirm')")
            if await submit_btn.count() > 0:
                await submit_btn.click()
                await page.wait_for_timeout(3000)

            # Verify application success (Look for success message)
            success_msg = page.locator("text='successfully applied', text='Application Sent'")
            if await success_msg.count() > 0:
                print(f"     ✅ Foundit Applied: {title} @ {company}")
                return ApplicationResult(job, "applied")
            
            # If no success message but also no obvious manual roadblock
            print(f"     ✅ Foundit Applied (Assumed): {title} @ {company}")
            return ApplicationResult(job, "applied")

        except Exception as e:
            print(f"     ❌ Foundit apply error: {e}")
            return ApplicationResult(job, "error", str(e))

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
                    
                    # Wait for job cards
                    job_cards = page.locator("div.job-apply-card, div.srpResultCard")
                    count = await job_cards.count()
                    if count == 0:
                        continue
                        
                    for i in range(min(count, 15)): # Limit to 15 per search
                        if applied_count >= daily_limit:
                            break
                            
                        card = job_cards.nth(i)
                        
                        try:
                            title_el = card.locator("h3, .jobTitle").first
                            title = await title_el.inner_text() if await title_el.count() > 0 else f"Job {i}"
                            
                            company_el = card.locator(".companyName").first
                            company = await company_el.inner_text() if await company_el.count() > 0 else "Unknown"
                            
                            link_el = card.locator("a[href*='/job']").first
                            job_url = await link_el.get_attribute("href") if await link_el.count() > 0 else search_url
                            if job_url and not job_url.startswith("http"):
                                job_url = self.base_url + job_url
                        except:
                            continue
                            
                        # Generate a deterministic ID based on title and company
                        job_id = f"fi_{title}_{company}".replace(" ", "_").lower()
                        if job_id in applied_today:
                            continue
                            
                        job = {
                            "id": job_id,
                            "title": title,
                            "company": company,
                            "location": city,
                            "url": job_url,
                            "portal": self.name
                        }
                        
                        if is_experienced_role(title, ""):
                            print(f"     ⏭️  Skipped: Requires experience (not fresher/intern)")
                            continue
                        
                        # Some versions of Foundit have quick apply directly on the card
                        quick_apply_btn = card.locator("button:has-text('Quick Apply')")
                        if await quick_apply_btn.count() > 0:
                            await quick_apply_btn.first.click()
                            await page.wait_for_timeout(3000)
                            
                            # Handle confirm modal
                            submit_btn = page.locator("button:has-text('Submit'), button:has-text('Confirm')")
                            if await submit_btn.count() > 0:
                                await submit_btn.click()
                                await page.wait_for_timeout(3000)
                                
                            results.append(ApplicationResult(job, "applied"))
                            applied_count += 1
                            applied_today.add(job_id)
                        else:
                            # Open job details to apply
                            result = await self.apply_to_job(page, job)
                            results.append(result)
                            if result.status == "applied":
                                applied_count += 1
                                applied_today.add(job_id)
                                
                            if page.url != search_url:
                                await page.goto(search_url, timeout=60000)
                                await page.wait_for_timeout(3000)
                                
                except Exception as e:
                    print(f"  ❌ Foundit search error [{role}/{city}]: {e}")
                    
        return results
