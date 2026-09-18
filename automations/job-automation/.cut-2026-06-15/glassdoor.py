import asyncio
from playwright.async_api import Page, TimeoutError

from .base import BasePortal, ApplicationResult

class GlassdoorPortal(BasePortal):
    name = "glassdoor"
    base_url = "https://www.glassdoor.co.in"
    login_url = "https://www.glassdoor.co.in/profile/login_input.htm"

    async def login(self, page: Page) -> bool:
        """
        Login to Glassdoor.
        Because Glassdoor uses aggressive bot protections (Cloudflare/CAPTCHA),
        we use slow typing and waits.
        """
        try:
            # Check if already logged in by looking for the profile icon or dashboard element
            await page.goto(self.base_url, timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Simple check for logged-in state
            if await page.locator("div[data-test='user-avatar']").count() > 0 or await page.locator("button[aria-label='Profile']").count() > 0 or await page.locator("nav").count() > 0 or "Community" in page.url or "member" in page.url:
                print("  ✅ Glassdoor: session active — skipping login")
                return True

            print("  🔑 Glassdoor: logging in...")
            await page.goto(self.login_url)
            await page.wait_for_timeout(3000)
            
            # Double check if it redirected to dashboard
            if "Community" in page.url or "member" in page.url or await page.locator("nav").count() > 0:
                print("  ✅ Glassdoor: session active — skipping login")
                return True

            # Fill email only if input exists
            email_input = page.locator("input[name='username'], input[type='email']")
            if await email_input.count() > 0 and await email_input.first.is_visible(timeout=3000):
                await email_input.first.fill(self.email)
                await page.wait_for_timeout(1000)
                
                # Click continue if there is a separate step for password
                if await page.locator("button[name='submit']").count() > 0:
                    await page.click("button[name='submit']")
                    await page.wait_for_timeout(2000)

            # Fill password
            if await page.locator("input[name='password']").count() > 0:
                await page.fill("input[name='password']", self.password)
                await page.wait_for_timeout(1000)
                await page.click("button[name='submit']")
                await page.wait_for_timeout(5000)
            
            # Verify login success
            if await page.locator("div[data-test='user-avatar']").count() > 0 or await page.locator("button[aria-label='Profile']").count() > 0:
                print("  ✅ Glassdoor: login successful")
                return True
            else:
                print("  ⚠️  Glassdoor: login might require CAPTCHA or OTP.")
                # We wait a bit to allow manual intervention if headful mode is on
                print("  ⏳ You have 60 seconds to manually solve the CAPTCHA/OTP in the browser window...")
                await page.wait_for_timeout(60000)
                return await page.locator("div[data-test='user-avatar']").count() > 0 or await page.locator("button[aria-label='Profile']").count() > 0

        except Exception as e:
            print(f"  ❌ Glassdoor login error: {e}")
            return False

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        """
        Applies to a job using Glassdoor's Easy Apply.
        """
        title = job.get("title", "Unknown Role")
        company = job.get("company", "Unknown Company")
        job_url = job.get("url")

        if not job_url:
            return ApplicationResult(job, "error", "No URL provided")

        try:
            print(f"  → {title} @ {company}")
            
            # If we are not on the search page, navigate to the job url
            if "jobs.htm" not in page.url.lower():
                await page.goto(job_url, timeout=60000)
                await page.wait_for_timeout(3000)

            # Close any annoying modals (like newsletter or profile prompts) that intercept clicks
            try:
                modal_close = page.locator("dialog button.CloseButton, dialog button[aria-label='Close'], button[data-test='close-button']").first
                if await modal_close.is_visible(timeout=500):
                    await modal_close.click()
                else:
                    await page.keyboard.press("Escape")
                await page.wait_for_timeout(1000)
            except:
                pass

            # Look for the Easy Apply button
            easy_apply_btn = page.locator("button[data-test='easyApplyButton'], button:has-text('Easy Apply')").first
            if await easy_apply_btn.count() == 0:
                print(f"     ⏭️  Glassdoor: Skipping job. No Easy Apply button.")
                return ApplicationResult(job, "skipped", "No Easy Apply button")

            # Glassdoor's Easy Apply button sometimes opens the modal in a brand new tab!
            # We must catch the new tab if it spawns, or fall back to the current page.
            modal_page = page
            try:
                async with page.context.expect_page(timeout=5000) as new_page_info:
                    await easy_apply_btn.click(force=True)
                modal_page = await new_page_info.value
                await modal_page.wait_for_load_state()
            except TimeoutError:
                # No new tab opened, it opened in the same page.
                # (Click might have already fired, but if it didn't we click again safely)
                pass

            await modal_page.wait_for_timeout(2000)
            if "indeed.com" in modal_page.url:
                print("     ⏳ Glassdoor: Detected Indeed inline form. Waiting 15 seconds for it to load...")
                await modal_page.wait_for_timeout(15000)

            # Easy Apply workflow
            # This is a simplified loop that clicks "Next" until "Submit" is found or it hits a wall.
            max_steps = 10
            for step in range(max_steps):
                # Wait for React to render the form (especially on step 0 for smartapply.indeed.com)
                try:
                    await modal_page.wait_for_selector("button:has-text('Continue'), button:has-text('Next'), button:has-text('Submit'), button:has-text('Apply'), .ia-continueButton, .ia-submitButton", timeout=6000)
                except:
                    pass
                    
                # Branch locators based on whether it's an Indeed inline form or native Glassdoor
                if "indeed.com" in modal_page.url:
                    submit_btn = modal_page.locator(".ia-submitButton, button:has-text('Submit application'), button:has-text('Submit your application')")
                    next_btn = modal_page.locator(".ia-continueButton, button:has-text('Continue'), button:has-text('Review your application'), button:has-text('Use your Indeed Resume'), button:has-text('Apply with this resume')")
                else:
                    submit_btn = modal_page.locator("button:has-text('Submit'), button:has-text('Apply'), [role='button']:has-text('Submit'), [role='button']:has-text('Apply'), input[type='submit']")
                    next_btn = modal_page.locator("button:has-text('Continue'), button:has-text('Next'), button:has-text('Review'), [role='button']:has-text('Continue'), [role='button']:has-text('Next')")

                if await submit_btn.count() > 0:
                    await submit_btn.last.click(force=True)
                    await modal_page.wait_for_timeout(4000)
                    
                    # Verify submission success for smartapply.indeed.com
                    if "indeed.com" in modal_page.url:
                        success = False
                        for sel in [".ia-PostApply", "h1:has-text('application was sent')", ":has-text('Your application has been submitted')", ":has-text('successfully applied')"]:
                            if await modal_page.locator(sel).count() > 0:
                                success = True
                                break
                                
                        if not success:
                            # It clicked submit but didn't go through (likely a missing required field)
                            print(f"     ⚠️  Glassdoor: Indeed form rejected submission. Skipping job.")
                            if modal_page != page:
                                await modal_page.close()
                            return ApplicationResult(job, "skipped", "Indeed form rejected submission")
                    
                    print(f"     ✅ Glassdoor Applied: {title} @ {company}")
                    if modal_page != page:
                        await modal_page.close()
                    return ApplicationResult(job, "applied")

                # Aggressive fallback: Fill any empty text fields, radios, checkboxes, and dropdowns
                try:
                    inputs = modal_page.locator("input[type='text'], input[type='number'], input[type='tel'], textarea")
                    count = await inputs.count()
                    for i in range(count):
                        if await inputs.nth(i).is_visible(timeout=200) and not await inputs.nth(i).input_value():
                            # Smart filling based on context
                            ctx = ((await inputs.nth(i).get_attribute("name")) or "").lower()
                            if "phone" in ctx or await inputs.nth(i).get_attribute("type") == "tel":
                                await inputs.nth(i).fill(os.getenv("USER_PHONE", "+910000000000"))
                            elif await inputs.nth(i).get_attribute("type") == "number":
                                await inputs.nth(i).fill("0")
                            else:
                                await inputs.nth(i).fill("1")
                except:
                    pass

                try:
                    radios = modal_page.locator("input[type='radio']")
                    count = await radios.count()
                    for i in range(count):
                        if await radios.nth(i).is_visible(timeout=200) and not await radios.nth(i).is_checked():
                            await radios.nth(i).click(force=True)
                except:
                    pass
                
                try:
                    checkboxes = modal_page.locator("input[type='checkbox']")
                    count = await checkboxes.count()
                    for i in range(count):
                        if await checkboxes.nth(i).is_visible(timeout=200) and not await checkboxes.nth(i).is_checked():
                            await checkboxes.nth(i).click(force=True)
                except:
                    pass
                
                try:
                    selects = modal_page.locator("select")
                    count = await selects.count()
                    for i in range(count):
                        if await selects.nth(i).is_visible(timeout=200):
                            opts = await selects.nth(i).locator("option").all()
                            for opt in opts:
                                val = await opt.get_attribute("value")
                                if val and val.lower() not in ["", "0", "select", "none", "please select"]:
                                    await selects.nth(i).select_option(val)
                                    break
                except:
                    pass

                if await next_btn.count() > 0:
                    await next_btn.last.click(force=True)
                    await modal_page.wait_for_timeout(1500)
                else:
                    # No Next and no Submit - form might be asking for specific fields we can't auto-fill
                    print(f"     ⚠️  Glassdoor: Form stuck at step {step}. Skipping job.")
                    if modal_page != page:
                        await modal_page.close()
                    return ApplicationResult(job, "skipped", "Stuck in Easy Apply modal")

            print(f"     ⚠️  Glassdoor: Reached maximum steps in Easy Apply. Skipping job.")
            if modal_page != page:
                await modal_page.close()
            return ApplicationResult(job, "skipped", "Exceeded max apply steps")

        except Exception as e:
            print(f"     ❌ Glassdoor apply error: {e}")
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
                    
                print(f"\n  🔍 Glassdoor: Searching for '{role}' in '{city}'")
                try:
                    # Navigate to search URL
                    search_url = f"{self.base_url}/Job/jobs.htm?sc.keyword={role.replace(' ', '%20')}&locT=C&locName={city.replace(' ', '%20')}"
                    await page.goto(search_url, timeout=60000)
                    await page.wait_for_timeout(4000)
                    
                    # Wait for job cards
                    job_cards = page.locator("li[data-test='jobListing']")
                    count = await job_cards.count()
                    if count == 0:
                        continue
                        
                    # Extract jobs using JS to avoid stale elements and clicking issues
                    job_data = await page.evaluate("""() => {
                        const out = [];
                        const cards = document.querySelectorAll("li[data-test='jobListing']");
                        cards.forEach(card => {
                            const a = card.querySelector("a[data-test='job-title']") || card.querySelector("a[id*='job-title']") || card.querySelector("a[href*='/job-listing/']");
                            const href = a ? a.href : '';
                            const title = a ? a.innerText.trim() : 'Unknown Role';
                            
                            const compEl = card.querySelector("span[data-test='employer-short-name']") || card.querySelector(".EmployerProfile_employerName__Cq2so") || card.querySelector("span[class*='EmployerProfile']");
                            const company = compEl ? compEl.innerText.trim() : 'Unknown Company';
                            
                            // Check if Easy Apply badge exists in the card's HTML
                            const isEasyApply = card.innerHTML.includes('Easy Apply');
                            
                            if (title && href) {
                                out.push({title, company, url: href, isEasyApply});
                            }
                        });
                        return out;
                    }""")
                    
                    for jd in job_data:
                        if applied_count >= daily_limit:
                            break
                            
                        # Generate deterministic ID
                        job_id = f"gd_{jd['title']}_{jd['company']}".replace(" ", "_").lower()
                        if job_id in applied_today:
                            continue
                            
                        job = {
                            "id": job_id,
                            "title": jd['title'],
                            "company": jd['company'],
                            "location": city,
                            "url": jd['url'],
                            "portal": self.name
                        }
                        
                        # If the search card didn't even have the Easy Apply badge, skip it immediately
                        if not jd.get('isEasyApply'):
                            print(f"  → {jd['title']} @ {jd['company']}")
                            print(f"     ⏭️  Glassdoor: Skipping job. No Easy Apply badge on card.")
                            results.append(ApplicationResult(job, "skipped", "No Easy Apply badge"))
                            continue
                            
                        # Open a fresh page for the application (Indeed-style isolation)
                        apply_page = await page.context.new_page()
                        try:
                            result = await self.apply_to_job(apply_page, job)
                        except Exception as e:
                            result = ApplicationResult(job, "error", str(e))
                        finally:
                            try:
                                await apply_page.close()
                            except:
                                pass
                                
                        results.append(result)
                        if result.status == "applied":
                            applied_count += 1
                            applied_today.add(job_id)
                            
                except Exception as e:
                    print(f"  ❌ Glassdoor search error [{role}/{city}]: {e}")
                    
        return results
