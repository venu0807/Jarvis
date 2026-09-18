from typing import Optional
from playwright.async_api import Page, TimeoutError

from .base import BasePortal, ApplicationResult

class UnstopPortal(BasePortal):
    name = "unstop"
    base_url = "https://unstop.com"
    login_url = "https://unstop.com/login"

    async def login(self, page: Page) -> bool:
        """
        Login to Unstop.
        """
        try:
            await page.goto(self.base_url, timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Check if already logged in by looking for a profile element (e.g. avatar)
            if await page.locator("img.user-avatar").count() > 0 or await page.locator("a[href='/user/profile']").count() > 0:
                print("  ✅ Unstop: session active — skipping login")
                return True

            print("  🔑 Unstop: logging in...")
            await page.goto(self.login_url)
            await page.wait_for_timeout(2000)

            # Look for email login button (Unstop often has Google/LinkedIn SSO default)
            # Unstop might ask to choose account type first
            candidate_btn = page.locator("div[aria-label='Login as Candidate']")
            if await candidate_btn.count() > 0 and await candidate_btn.first.is_visible(timeout=3000):
                await candidate_btn.first.click()
                await page.wait_for_timeout(2000)

            email_login_btn = page.locator("button:has-text('Login with Email'), div:has-text('Login with Email')")
            if await email_login_btn.count() > 0 and await email_login_btn.first.is_visible(timeout=3000):
                await email_login_btn.first.click()
                await page.wait_for_timeout(1000)

            # Fill email only if input exists
            email_input = page.locator("input[name='email'], input[type='email']")
            if await email_input.count() > 0 and await email_input.first.is_visible(timeout=3000):
                await email_input.first.fill(self.email)
                
                pass_input = page.locator("input[name='password'], input[type='password']")
                if await pass_input.count() > 0:
                    await pass_input.first.fill(self.password)
                    
                await page.click("button[type='submit'], button:has-text('Login')")
            
            await page.wait_for_timeout(5000)
            
            # Verify login success
            if await page.locator("img.user-avatar").count() > 0 or await page.locator("img[alt*='avatar']").count() > 0 or await page.locator("a[href='/user/profile']").count() > 0:
                print("  ✅ Unstop: login successful")
                return True
            else:
                print("  ⚠️  Unstop: login might require manual CAPTCHA/OTP.")
                print("  ⏳ You have 60 seconds to manually solve it in the browser window...")
                await page.wait_for_timeout(60000)
                return await page.locator("img.user-avatar").count() > 0 or await page.locator("img[alt*='avatar']").count() > 0

        except Exception as e:
            print(f"  ❌ Unstop login error: {e}")
            return False

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        """
        Applies to a job using Unstop's internal Apply flow.
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
            
            # Check Eligibility section strictly for "Fresher"
            try:
                page_text = await page.locator("body").inner_text()
                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                for i, line in enumerate(lines):
                    if line == "Eligibility":
                        if i + 1 < len(lines):
                            eligibility_val = lines[i+1].lower()
                            # If it explicitly lists eligibility but DOES NOT include fresher
                            if "fresher" not in eligibility_val:
                                print(f"     ⏭️  Unstop: Skipping job. Eligibility is '{lines[i+1]}', not Fresher.")
                                return ApplicationResult(job, "skipped", f"Eligibility: {lines[i+1]}")
                        break
            except Exception as e:
                pass # If checking fails, proceed anyway

            # Look for the Apply button
            apply_btn = page.locator("button:has-text('Apply'), button:has-text('Register'), a:has-text('Apply'), a:has-text('Register'), .register_btn, .apply-btn, div:has-text('Quick Apply')")
            if await apply_btn.count() == 0:
                print(f"     ⚠️  Unstop: Apply/Register button not found.")
                return ApplicationResult(job, "manual", "No Apply button")

            # Click Apply
            num_pages_before = len(page.context.pages)
            await apply_btn.first.click(force=True)
            await page.wait_for_timeout(6000) # Increased wait to allow full SPA navigation to /register
            
            # Check if a new tab was opened (External redirect)
            if len(page.context.pages) > num_pages_before:
                new_page = page.context.pages[-1]
                print(f"     ⚠️  Unstop: Redirected to external site. Falling back to manual.")
                try:
                    await new_page.close()
                except:
                    pass
                return ApplicationResult(job, "manual", "External redirect")

            # Handle multi-step application forms (up to 5 steps)
            for step in range(5):
                await page.wait_for_timeout(2000)
                
                # Check for Terms & Conditions or other required checkboxes and check them
                checkboxes = page.locator("input[type='checkbox']")
                count = await checkboxes.count()
                for i in range(count):
                    try:
                        if not await checkboxes.nth(i).is_checked():
                            await checkboxes.nth(i).check(force=True)
                    except:
                        pass
                        
                # Handle 'Differently Abled' question which sometimes blocks progression
                try:
                    if await page.locator("text='Differently Abled'").count() > 0:
                        no_btn = page.get_by_text("No", exact=True)
                        if await no_btn.count() > 0:
                            await no_btn.first.click(force=True)
                except:
                    pass
                    
                # Aggressive fallback: Fill any empty text fields with "NA" or "0" to brute-force validation
                inputs = page.locator("input[type='text'], input[type='number'], textarea")
                count = await inputs.count()
                for i in range(count):
                    try:
                        if not await inputs.nth(i).input_value():
                            if await inputs.nth(i).get_attribute("type") == "number":
                                await inputs.nth(i).fill("0")
                            else:
                                await inputs.nth(i).fill("NA")
                    except:
                        pass
                
                # Look for progression buttons (broadened to include a tags and divs)
                submit_btn = page.locator("button[type='submit'], button:has-text('Submit'), button:has-text('Proceed'), button:has-text('Next'), button:has-text('Done'), button:has-text('Register'), button:not(.register_btn):has-text('Apply'), button:has-text('Confirm'), button:has-text('Yes'), a:has-text('Next'), div.btn:has-text('Next')")
                if await submit_btn.count() > 0:
                    # Click the last matching button (usually the primary one at the bottom right)
                    await submit_btn.last.click(force=True)
                    await page.wait_for_timeout(5000) # Wait for next step to load
                else:
                    break # No more next buttons found
                    
            await page.wait_for_timeout(2000)
            # Verification: check if the button changed to "Registered" or if a success message exists
            success_indicators = page.locator("div.register_btn:has-text('Registered'), button:has-text('Registered'), div.register_btn:has-text('Applied'), button:has-text('Applied'), div:has-text('Applied Successfully'), div:has-text('Registered Successfully')")
            if await success_indicators.count() > 0:
                print(f"     ✅ Unstop Applied: {title} @ {company}")
                return ApplicationResult(job, "applied")
                
            # If the Quick Apply button is still there, it means we didn't apply (e.g. modal is stuck)
            if await page.locator(".register_btn:has-text('Quick Apply')").count() > 0 or await page.locator("button:has-text('Apply Now')").count() > 0:
                print(f"     ⚠️  Unstop: Complex application form detected. Falling back to manual.")
                return ApplicationResult(job, "manual", "Complex form or external redirect")
            
            # If we are stuck on the /register page, we failed to complete the form
            if "/register" in page.url or "/apply" in page.url:
                print(f"     ⚠️  Unstop: Form incomplete. Falling back to manual.")
                return ApplicationResult(job, "manual", "Form incomplete")
            
            # If the button is gone but we didn't see "Registered", assume success if URL didn't change to an external site
            if "unstop.com" in page.url:
                print(f"     ✅ Unstop Applied: {title} @ {company}")
                return ApplicationResult(job, "applied")
            
            print(f"     ⚠️  Unstop: Redirected to external site. Falling back to manual.")
            return ApplicationResult(job, "manual", "External redirect")

        except Exception as e:
            print(f"     ❌ Unstop apply error: {e}")
            return ApplicationResult(job, "error", str(e))

    async def search_and_apply(self, page: Page, roles: list, cities: list, daily_limit: int, applied_today: set) -> list:
        """
        Searches for jobs and applies to them.
        """
        results = []
        applied_count = 0
        
        for role in roles:
            # Unstop search is usually global or remote-heavy, but we pass city if possible
            for city in cities:
                if applied_count >= daily_limit:
                    break
                    
                print(f"\n  🔍 Unstop: Searching for '{role}' in '{city}'")
                try:
                    # Construct the direct search URL for jobs, including only open applications and 'fresher' in search term
                    search_url = f"{self.base_url}/job?oppstatus=open&searchTerm={role.replace(' ', '%20')}%20fresher"
                    
                    print(f"  🔍 Unstop: Searching at {search_url}")
                    await page.goto(search_url, timeout=60000)
                    
                    # Wait for the search results to render
                    await page.wait_for_timeout(5000)
                    
                    # The actual job cards on the search results use the 'a.item' class
                    job_cards = page.locator("a.item")
                    count = await job_cards.count()
                    
                    if count == 0:
                        print(f"  ❌ Unstop: No jobs found for '{role}' in '{city}'.")
                        continue
                        
                    for i in range(min(count, 10)): # Limit to 10 per search
                        if applied_count >= daily_limit:
                            break
                            
                        # Re-locate cards in case of DOM changes
                        job_cards = page.locator("a.item")
                        if i >= await job_cards.count():
                            break
                            
                        card = job_cards.nth(i)
                        
                        try:
                            # Extract title from h2/h3
                            title_el = card.locator("h2, h3").first
                            title = await title_el.inner_text() if await title_el.count() > 0 else f"Job {i}"
                            
                            # Extract company from paragraph
                            company_el = card.locator("p.single-wrap, .organization-name").first
                            company = await company_el.inner_text() if await company_el.count() > 0 else "Unknown"
                            
                            # Generate a deterministic ID based on title and company
                            job_id = f"us_{title}_{company}".replace(" ", "_").lower()
                            if job_id in applied_today:
                                continue
                                
                            job = {
                                "id": job_id,
                                "title": title,
                                "company": company,
                                "location": city,
                                "url": page.url, # We don't have direct URLs, we click
                                "portal": self.name
                            }
                            
                            # Click the card to open job details in a new tab
                            async with page.context.expect_page(timeout=15000) as new_page_info:
                                await card.click(force=True)
                            new_page = await new_page_info.value
                            await new_page.wait_for_load_state()
                            await new_page.wait_for_timeout(5000)
                            
                            # Update the URL since it navigated
                            job["url"] = new_page.url
                            
                            # Unstop often redirects completely to apply, so we call apply_to_job
                            result = await self.apply_to_job(new_page, job)
                            results.append(result)
                            
                            if result.status == "applied":
                                applied_count += 1
                                applied_today.add(job_id)
                                
                            # Close the newly opened tab
                            await new_page.close()
                            
                        except Exception as e:
                            print(f"  ❌ Unstop card error: {e}")
                            # Close the new page if it was created but crashed
                            try:
                                if 'new_page' in locals() and not new_page.is_closed():
                                    await new_page.close()
                            except:
                                pass
                            
                except Exception as e:
                    print(f"  ❌ Unstop search error [{role}/{city}]: {e}")
                    
        return results
