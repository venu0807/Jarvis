"""
portals/internshala.py — Internshala Easy Apply with persistent session
- Session via storage_state (managed by auto_applier.py)
- Auto-generates short cover letter for jobs that require one
- Handles availability, start date, screening question detection
"""
import os
import random
from playwright.async_api import Page
from .base import BasePortal, ApplicationResult, is_experienced_role

TIMEOUT = 45_000

GENERIC_COVER_LETTER = (
    "I am excited to apply for this position. With my background in Python, Django, "
    "REST APIs, and machine learning (CNN-based systems achieving 89% accuracy), "
    "I am confident I can contribute meaningfully from day one. "
    f"I am a quick learner, currently pursuing MCA (AI/ML) at {os.getenv('USER_UNIVERSITY', 'my university')}, "
    "and I am available to start immediately. Looking forward to the opportunity."
)


class InternshalaPortal(BasePortal):
    name = "Internshala"
    base_url = "https://internshala.com"
    login_url = "https://internshala.com/login/student"

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, page: Page) -> bool:
        try:
            await page.goto(self.base_url, wait_until="networkidle", timeout=TIMEOUT)
            await page.wait_for_timeout(1500)

            if await self._is_logged_in(page):
                print("  ✅ Internshala: session active — skipping login")
                return True

            await page.goto(self.login_url, wait_until="networkidle", timeout=TIMEOUT)
            await page.wait_for_timeout(2000)

            # Close any annoying cookie/promo modals if they overlay the page
            try:
                await page.click(".close, .modal-close, [aria-label='Close']", timeout=2000)
            except:
                pass

            # Check if redirected to dashboard automatically
            if await self._is_logged_in(page):
                print("  ✅ Internshala: logged in automatically via redirect")
                return True

            try:
                # The original robust fill logic
                await page.fill("#email", self.email)
                await page.wait_for_timeout(400)
                await page.fill("#password", self.password)
                await page.wait_for_timeout(400)
                await page.click("#login_submit")
                await page.wait_for_timeout(4000)
            except Exception as login_err:
                print(f"  ❌ Internshala: Failed to find or fill login form: {login_err}")
                return False

            if await self._is_logged_in(page):
                print("  ✅ Internshala: logged in")
                return True

            print("  ❌ Internshala: login failed")
            return False

        except Exception as e:
            print(f"  ❌ Internshala login error: {e}")
            return False

    async def _is_logged_in(self, page: Page) -> bool:
        try:
            # Check for elements that only exist when logged in:
            # Profile dropdowns, logout buttons, or the chat icon
            selectors = [
                ".profile-pic", ".student-profile", "#profile-dropdown", 
                ".profile_container", ".nav-profile-icon", 
                "a[href*='/logout']", "a:has-text('Logout')",
                ".chat-icon-container", "#bookmark"
            ]
            await page.wait_for_selector(", ".join(selectors), timeout=3000)
            return True
        except:
            # Fallback: if we are redirected to dashboard, we are logged in
            if "/dashboard" in page.url or "/student" in page.url:
                # Unless it's the login page itself
                if "/login" not in page.url:
                    return True
            return False

    # ── Apply ─────────────────────────────────────────────────────────────────

    async def search_and_apply(self, page: Page, roles: list, cities: list, limit: int, applied_today: set) -> list:
        results = []
        applied = 0
        
        print("  🔄 Internshala: Fetching recommended jobs as per your preferences...")
        
        search_url = "https://internshala.com/jobs/"
        
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(4000)
            
            # Close any annoying popups
            try: await page.locator("#close_popup, .close, .modal-close").first.click(timeout=1000)
            except: pass
            
            # Extract job cards
            jobs_found = []
            cards = await page.locator(".individual_internship").all()
            
            for card in cards:
                try:
                    # Skip ads
                    class_name = await card.get_attribute("class") or ""
                    if "jos_native_ad" in class_name:
                        continue
                        
                    title_el = card.locator("a.job-title-href, .job-internship-name a, .heading_4_5 a").first
                    if not await title_el.is_visible(timeout=500): continue
                    title = await title_el.inner_text()
                    href = await title_el.get_attribute("href")
                    if not href.startswith("http"): href = "https://internshala.com" + href
                    
                    company = await card.locator(".company-name, .company_name").first.inner_text()
                    
                    # ID extraction
                    job_id_attr = await card.get_attribute("internshipid") or await card.get_attribute("jobid")
                    job_id = f"internshala_{job_id_attr}" if job_id_attr else f"internshala_{href.split('-')[-1]}"
                    
                    jobs_found.append({
                        "id": job_id,
                        "title": title.strip(),
                        "company": company.strip(),
                        "url": href,
                        "portal": "Internshala",
                        "location": "Preferences",
                        "description": ""
                    })
                except:
                    continue
                    
            print(f"  🔍 Internshala: Found {len(jobs_found)} recommended jobs matching preferences")
            
            for job in jobs_found:
                if applied >= limit: break
                if job["id"] in applied_today:
                    print(f"     ⏭️  Already applied: {job['title']}")
                    continue
                    
                print(f"\n  → {job['title']} @ {job['company']}")
                
                if is_experienced_role(job['title'], ""):
                    print(f"     ⏭️  Skipped: Requires experience (not fresher/intern)")
                    continue
                
                try:
                    # Use new page for apply to preserve search results
                    apply_page = await page.context.new_page()
                    result = await self.apply_to_job(apply_page, job)
                    
                    try: await apply_page.close()
                    except: pass
                    
                    results.append(result)
                    applied_today.add(job["id"])
                    
                    if result.status == "applied":
                        applied += 1
                    elif result.status == "manual":
                        print(f"     📋 Manual: {result.reason}")
                    elif result.status == "skipped":
                        print(f"     ⏭️  Skipped: {result.reason}")
                    elif result.status == "error":
                        print(f"     ❌ Error: {result.reason}")
                        
                except Exception as e:
                    print(f"     ⚠️  Apply error: {e}")
                    
                await page.wait_for_timeout(random.uniform(2000, 4000))

        except Exception as ex:
            print(f"  ❌ Internshala search: {str(ex)[:80]}")

        return results

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        try:
            await page.goto(job["url"], wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(random.uniform(2000, 3000))

            # --- Extract Job Description ---
            try:
                desc_el = page.locator(".detail_view, .text-container, .job_description").first
                if await desc_el.is_visible(timeout=1000):
                    job["description"] = (await desc_el.text_content()).strip()
            except:
                pass

            # Already applied?
            try:
                if await page.locator(":has-text('Already Applied'), .already_applied").first.is_visible(timeout=1500):
                    return ApplicationResult(job=job, status="skipped", reason="Already applied")
            except:
                pass

            # Click Apply Now
            clicked = False
            for sel in ["#apply_now_btn", ".apply_now_btn", "button:has-text('Apply Now')", "a:has-text('Apply Now')"]:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        await page.wait_for_timeout(2500)
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                return ApplicationResult(job=job, status="skipped", reason="Apply button not found")

            # Screening questions — auto-fill instead of skipping
            try:
                screening = page.locator(".assessment_questions, .questions-container, .screening_questions").first
                if await screening.is_visible(timeout=1500):
                    print(f"     📝 Answering screening questions...")
                    # Fill text inputs
                    text_inputs = await screening.locator("input[type='text'], input[type='number']").all()
                    for inp in text_inputs:
                        try:
                            if await inp.is_visible() and not await inp.input_value():
                                ph = (await inp.get_attribute("placeholder") or "").lower()
                                label_el = await inp.evaluate("e => e.closest('.form-group, .question')?.querySelector('label, .question-text')?.innerText || ''")
                                label = label_el.lower()
                                combined = ph + " " + label
                                if "experience" in combined or "year" in combined:
                                    await inp.fill("0")
                                elif "ctc" in combined or "salary" in combined or "income" in combined:
                                    await inp.fill("0")
                                elif "degree" in combined or "education" in combined or "qualification" in combined:
                                    await inp.fill("MCA")
                                elif "skill" in combined or "technology" in combined or "tools" in combined:
                                    await inp.fill("Python, Django, Machine Learning, React, JavaScript")
                                elif "notice" in combined:
                                    await inp.fill("Immediate")
                                elif "city" in combined or "location" in combined:
                                    await inp.fill("Delhi")
                                else:
                                    await inp.fill("Yes")
                        except:
                            continue
                    # Fill textareas
                    textareas = await screening.locator("textarea").all()
                    for ta in textareas:
                        try:
                            if await ta.is_visible() and not await ta.input_value():
                                await ta.fill("I am a fresher with strong skills in Python, Django, React, and ML. "
                                            "I am available to join immediately and eager to contribute.")
                        except:
                            continue
                    # Select radio buttons (first/yes option)
                    try:
                        radios = await screening.locator("input[type='radio']").all()
                        for radio in radios:
                            try:
                                label_text = await radio.evaluate("e => e.closest('label')?.innerText || e.nextElementSibling?.innerText || ''")
                                if label_text.strip().lower() in ["yes", "immediately", "0", "fresher"]:
                                    await radio.click()
                                    break
                            except:
                                continue
                    except:
                        pass
                    # Select dropdowns
                    try:
                        selects = await screening.locator("select").all()
                        for sel in selects:
                            if await sel.is_visible():
                                opts = await sel.locator("option").all()
                                if len(opts) > 1:
                                    val = await opts[1].get_attribute("value")
                                    await sel.select_option(val)
                    except:
                        pass
                    await page.wait_for_timeout(500)
            except:
                pass

            # Cover letter field — auto-fill
            try:
                cl = page.locator("textarea[name='cover_letter'], textarea[id*='cover'], textarea[placeholder*='cover']").first
                if await cl.is_visible(timeout=1500):
                    val = (await cl.input_value()) or ""
                    if not val.strip():
                        await cl.fill(GENERIC_COVER_LETTER)
                    await page.wait_for_timeout(500)
            except:
                pass

            # Availability / notice period field
            for sel in ["input[name*='availability']", "input[id*='availability']", "select[name*='notice']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=800):
                        tag = await el.evaluate("e => e.tagName.toLowerCase()")
                        if tag == "select":
                            await el.select_option(index=1)
                        else:
                            await el.fill("Immediately")
                    break
                except:
                    continue

            # Submit
            for sel in ["button:has-text('Submit')", "input[type='submit']", "button[type='submit']", "button:has-text('Apply')"]:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        await page.wait_for_timeout(3000)
                        # Check for success
                        if await self._is_applied(page):
                            print(f"     ✅ Internshala Applied: {job['title']} @ {job['company']}")
                            return ApplicationResult(job=job, status="applied")
                        # No explicit success message — assume applied
                        print(f"     ✅ Internshala Applied (no confirm): {job['title']} @ {job['company']}")
                        return ApplicationResult(job=job, status="applied")
                except:
                    continue

            return ApplicationResult(job=job, status="manual", reason="Submit button not found")

        except Exception as e:
            return ApplicationResult(job=job, status="error", reason=str(e))

    async def _is_applied(self, page: Page) -> bool:
        for sel in [
            ":has-text('successfully applied')",
            ":has-text('Application submitted')",
            ":has-text('applied successfully')",
            ".success-message",
            "#success-message",
        ]:
            try:
                if await page.locator(sel).first.is_visible(timeout=600):
                    return True
            except:
                pass
        return False
