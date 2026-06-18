"""
portals/linkedin.py — LinkedIn Easy Apply with persistent session support
- Session via storage_state (managed by auto_applier.py)
- Auto-fills phone, location, experience, Yes/No questions
- Only marks manual if open-text question can't be auto-answered
- Uses LinkedIn's saved profile/resume (no file upload)
"""
import os
import random
from playwright.async_api import Page
from .base import BasePortal, ApplicationResult, is_experienced_role

TIMEOUT  = 60_000
PHONE    = os.getenv("USER_PHONE", "+910000000000")
LOCATION = os.getenv("USER_LOCATION", "City, Country")
YEARS_EXP = "0"  # fresher


class LinkedInPortal(BasePortal):
    name = "LinkedIn"
    base_url = "https://www.linkedin.com"
    login_url = "https://www.linkedin.com/login"

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, page: Page) -> bool:
        try:
            # Fast session check — wait 1.5s max, not 3s
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(1500)

            if await self._is_logged_in(page):
                print("  ✅ LinkedIn: session active — skipping login")
                return True

            print("  🔑 LinkedIn: session expired, logging in")

            # Go to login page — domcontentloaded is enough, #username is in initial HTML
            await page.goto(self.login_url, wait_until="domcontentloaded", timeout=TIMEOUT)

            # Wait for the email field directly — fastest possible signal that the form is ready
            try:
                await page.wait_for_selector("#username", state="visible", timeout=15000)
            except:
                # Fallback: fixed wait
                await page.wait_for_timeout(2000)

            # Dismiss cookie banner only if it appears quickly (500ms check)
            for consent_sel in ["button:has-text('Accept')", "button:has-text('Accept all')"]:
                try:
                    btn = page.locator(consent_sel).first
                    if await btn.is_visible(timeout=500):
                        await btn.click()
                        await page.wait_for_timeout(400)
                        break
                except:
                    pass

            # Focus via JS (no visibility needed) then type via keyboard
            # keyboard.type() sends real keydown/keypress/keyup events per character
            # — React's form validation listens to these to enable Submit button
            focused_email = await page.evaluate("""() => {
                const sels = ['#username', 'input[autocomplete="username"]',
                               'input[name="session_key"]', 'input[type="email"]'];
                for (const sel of sels) {
                    const el = document.querySelector(sel);
                    if (el) { el.focus(); return true; }
                }
                return false;
            }""")

            if not focused_email:
                print(f"  ❌ LinkedIn: email field not found in DOM (URL: {page.url[:80]})")
                return False

            await page.wait_for_timeout(400)  # wait for CSS animation to settle
            await page.keyboard.type(self.email, delay=40)
            await page.wait_for_timeout(400)

            # Tab to password field (most reliable navigation between fields)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(200)

            # Verify focus moved to password, or focus it explicitly
            await page.evaluate("""() => {
                const active = document.activeElement;
                if (!active || active.type !== 'password') {
                    const el = document.querySelector('#password') ||
                               document.querySelector('input[type="password"]');
                    if (el) el.focus();
                }
            }""")
            await page.wait_for_timeout(200)
            await page.keyboard.type(self.password, delay=40)
            await page.wait_for_timeout(400)

            # Submit — press Enter (most reliable for login forms)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(5000)

            # Handle CAPTCHA / verification challenge
            if "checkpoint" in page.url or "challenge" in page.url or "authwall" in page.url:
                print("  ⚠️  LinkedIn: verification required — waiting 90s for manual solve")
                await page.wait_for_timeout(90_000)

            # If URL left /login/ → login succeeded, but page might still be loading
            current_url = page.url
            login_failed = any(x in current_url for x in ["login", "authwall", "checkpoint"])

            if not login_failed:
                # Navigate to /feed/ to ensure full session load before saving state
                if "/feed" not in current_url:
                    try:
                        await page.goto("https://www.linkedin.com/feed/",
                                        wait_until="domcontentloaded", timeout=TIMEOUT)
                        await page.wait_for_timeout(3000)
                    except:
                        pass
                print("  ✅ LinkedIn: logged in")
                return True

            print(f"  ❌ LinkedIn: login failed (URL: {current_url[:80]})")
            return False


        except Exception as e:
            print(f"  ❌ LinkedIn login error: {e}")
            return False

    async def _is_logged_in(self, page: Page) -> bool:
        # First check: URL is not a login/auth page
        url = page.url
        if any(x in url for x in ["linkedin.com/login", "authwall", "checkpoint"]):
            return False
        # Second check: we're on a LinkedIn page (not login) = logged in
        if "linkedin.com" in url and "login" not in url:
            return True
        # Fallback: look for nav element
        try:
            await page.wait_for_selector(
                ".global-nav, .feed-identity-module, [data-control-name='identity_profile_photo']",
                timeout=8000
            )
            return True
        except:
            return False

    # ── Search and Apply ──────────────────────────────────────────────────────

    async def search_and_apply(self, page: Page, role: str, location: str, daily_limit: int) -> list:
        results = []
        applied = 0
        try:
            url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={role.replace(' ', '%20')}"
                f"&location={location.replace(' ', '%20')}"
                f"&f_AL=true"        # Easy Apply only
                f"&f_E=1,2"          # 1=Internship, 2=Entry level
                f"&f_TPR=r86400"     # Posted last 24h
                f"&sortBy=DD"        # Newest first
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(2500)

            # Scroll list a bit to force React to render more cards
            try:
                await page.evaluate("""
                    let list = document.querySelector('.jobs-search__results-list');
                    if(list) list.scrollTop += 1000;
                """)
                await page.wait_for_timeout(1000)
            except:
                pass

            cards = await page.locator(".job-card-container, .jobs-search__results-list li").all()
            print(f"  🔍 LinkedIn: {len(cards)} jobs extracted for '{role}' in {location}")

            for card in cards:
                if applied >= daily_limit:
                    break

                # ── Close any open Easy Apply modal before clicking next card ──
                await self._close_any_modal(page)
                await page.wait_for_timeout(600)

                try:
                    # Scroll card into view and click
                    await card.scroll_into_view_if_needed()
                    await card.click(timeout=5000, force=True)
                    await page.wait_for_timeout(random.uniform(500, 800))

                    # Extract job info from right panel
                    title = ""
                    company = ""
                    job_url = page.url

                    for sel in [".job-details-jobs-unified-top-card__job-title", "h1.t-24", ".job-details-jobs-unified-top-card__job-title-link"]:
                        try:
                            title_el = page.locator(sel).first
                            if await title_el.is_visible(timeout=1000):
                                title = (await title_el.text_content()).strip()
                                break
                        except:
                            pass

                    for sel in [".job-details-jobs-unified-top-card__company-name", ".jobs-unified-top-card__company-name"]:
                        try:
                            comp_el = page.locator(sel).first
                            if await comp_el.is_visible(timeout=1000):
                                company = (await comp_el.text_content()).strip()
                                break
                        except:
                            pass

                    if not title:
                        continue
                        
                    print(f"\n  → {title} @ {company}")

                    description = ""
                    try:
                        desc_el = page.locator(".jobs-description-content__text, #job-details").first
                        if await desc_el.is_visible(timeout=1000):
                            description = (await desc_el.text_content()).strip()
                    except:
                        pass

                    job = {
                        "id": f"linkedin_{abs(hash(job_url)) % 999999}",
                        "title": title,
                        "company": company,
                        "location": location,
                        "portal": "LinkedIn",
                        "url": job_url,
                        "description": description,
                    }

                    if is_experienced_role(title, description):
                        print(f"     ⏭️  Skipped: Requires experience (not fresher/intern)")
                        await self._close_any_modal(page)
                        continue

                    # We run _easy_apply directly on the main page (right pane)
                    result = await self._easy_apply(page, job)
                    results.append(result)
                    
                    if result.status == "applied":
                        applied += 1
                    elif result.status == "manual":
                        print(f"     📋 Manual: {result.reason}")
                    elif result.status == "skipped":
                        print(f"     ⏭️  Skipped: {result.reason}")
                    elif result.status == "error":
                        print(f"     ❌ Error: {result.reason}")

                    # Always close any modal left open by _easy_apply before next card
                    await self._close_any_modal(page)
                    await page.wait_for_timeout(random.uniform(700, 1000))

                except Exception as ex:
                    short_err = str(ex).split("\n")[0][:120]
                    print(f"     ⚠️  Card error: {short_err}")
                    await self._close_any_modal(page)
                    continue

        except Exception as e:
            print(f"  ❌ LinkedIn search error: {e}")

        return results

    # ── Modal dismissal ────────────────────────────────────────────────────

    async def _close_any_modal(self, page: Page):
        """
        Close any open Easy Apply modal or discard confirmation dialog.
        Uses Escape key first (most reliable), then button clicks as fallback.
        """
        try:
            # Check if any modal is actually open before trying to close
            modal = page.locator(
                "[data-test-modal-id='easy-apply-modal'], "
                "[data-test-modal-id='data-test-easy-apply-discard-confirmation'], "
                "[data-test-modal-container]"
            ).first
            if not await modal.is_visible(timeout=800):
                return  # No modal open
        except:
            return

        # Try Escape key first
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(600)
        except:
            pass

        # Check if discard confirmation appeared
        try:
            discard = page.locator(
                "button:has-text('Discard'), "
                "[data-test-dialog-primary-btn]"
            ).first
            if await discard.is_visible(timeout=800):
                await discard.click()
                await page.wait_for_timeout(400)
        except:
            pass

        # Final check — click X button if modal still open
        try:
            close_btn = page.locator(
                "button[aria-label='Dismiss'], button[aria-label='Close']"
            ).first
            if await close_btn.is_visible(timeout=500):
                await close_btn.click()
                await page.wait_for_timeout(400)
                # Confirm discard if prompted
                try:
                    discard = page.locator("button:has-text('Discard')").first
                    if await discard.is_visible(timeout=500):
                        await discard.click()
                except:
                    pass
        except:
            pass

    # ── Easy Apply flow ────────────────────────────────────────────────────

    async def _easy_apply(self, page: Page, job: dict) -> ApplicationResult:
        try:
            # Find and click the native Apply button (can be "Easy Apply" or "Apply" with 'in' logo)
            # We poll the DOM because LinkedIn's React UI can take a few seconds to render
            easy_apply_clicked = False
            for attempt in range(3):
                try:
                    # First pass: look specifically for "Easy Apply" text
                    buttons = await page.locator("button:has-text('Apply'), .jobs-apply-button").all()
                    easy_apply_btn = None
                    for btn in buttons:
                        txt = (await btn.text_content() or "").lower()
                        if "filter" in txt:
                            continue
                        # Prefer buttons with "Easy Apply" text
                        if "easy apply" in txt or "easyapply" in txt:
                            easy_apply_btn = btn
                            break
                        # Fallback: any Apply button
                        if not easy_apply_btn:
                            easy_apply_btn = btn
                    
                    if not easy_apply_btn:
                        return ApplicationResult(job=job, status="skipped", reason="No Easy Apply button — apply directly on portal")
                    
                    txt = (await easy_apply_btn.text_content() or "").lower()
                    is_vis = await easy_apply_btn.is_visible()
                    if is_vis:
                        pages_before = len(page.context.pages)
                        await easy_apply_btn.click(timeout=2000)
                        await page.wait_for_timeout(1000)
                        
                        # If a new tab opened, it's an external company site link
                        if len(page.context.pages) > pages_before:
                            new_page = page.context.pages[-1]
                            await new_page.close()
                            return ApplicationResult(job=job, status="skipped", reason="External company site apply — skipped")
                            
                        easy_apply_clicked = True
                        break
                except Exception as e:
                    pass
                    
                if easy_apply_clicked:
                    break
                await page.wait_for_timeout(800)

            if not easy_apply_clicked:
                return ApplicationResult(job=job, status="skipped", reason="No Easy Apply button — apply directly on portal")

            # Walk through form steps (up to 10)
            for step in range(10):
                await page.wait_for_timeout(500)

                # Submitted?
                if await self._is_submitted(page):
                    try:
                        await page.click("button:has-text('Done')", timeout=2000)
                    except:
                        pass
                    print(f"     ✅ LinkedIn Applied: {job['title']} @ {job['company']}")
                    return ApplicationResult(job=job, status="applied")

                # Open-text question (textarea) → auto-fill with canned response
                try:
                    ta = page.locator("div[data-test-form-element] textarea, .jobs-easy-apply-modal textarea")
                    if await ta.first.is_visible(timeout=600):
                        ta_count = await ta.count()
                        filled_any = False
                        for t_idx in range(ta_count):
                            t_el = ta.nth(t_idx)
                            if await t_el.is_visible(timeout=300):
                                val = await t_el.input_value()
                                if not val:
                                    cols = await t_el.get_attribute("cols") or "0"
                                    if int(cols) > 20:
                                        await t_el.fill("I am a Full Stack AI Engineer with hands-on experience building ML-integrated applications using Python, Django, and React. I am eager to contribute my skills and grow with your team.")
                                    else:
                                        await t_el.fill("https://github.com/pvgreddy")
                                    filled_any = True
                        if filled_any:
                            await page.wait_for_timeout(300)
                        else:
                            await self._close_any_modal(page)
                            return ApplicationResult(job=job, status="manual", reason="Open text question — apply manually")
                except:
                    pass

                # ── Yes/No radio questions (LinkedIn fieldset pattern) ────────
                try:
                    fieldsets = page.locator("fieldset")
                    fcount = await fieldsets.count()
                    for fi in range(fcount):
                        fs = fieldsets.nth(fi)
                        if not await fs.is_visible(timeout=400):
                            continue
                        # Try to click the "Yes" label/radio within this fieldset
                        yes_clicked = False
                        for yes_sel in [
                            "label:has-text('Yes')",
                            "input[type='radio'][value='Yes']",
                            "input[type='radio'][value='yes']",
                            "span:has-text('Yes')",
                        ]:
                            try:
                                yes_el = fs.locator(yes_sel).first
                                if await yes_el.is_visible(timeout=400):
                                    await yes_el.click()
                                    yes_clicked = True
                                    await page.wait_for_timeout(300)
                                    break
                            except:
                                continue
                        if not yes_clicked:
                            # Fallback: click first radio in fieldset
                            try:
                                first_radio = fs.locator("input[type='radio']").first
                                if await first_radio.is_visible(timeout=400):
                                    if not await first_radio.is_checked():
                                        await first_radio.click()
                            except:
                                pass
                except:
                    pass

                # Fill all visible simple fields
                await self._fill_step(page)

                # Click Next / Continue / Review / Submit
                # LinkedIn has rolled out 3 button variants in 2025-2026: "Next" / "Continue" / "Review"
                # Click whichever visible, not-disabled CTA is in the modal
                navigated = False
                cta_selectors = [
                    "button[aria-label*='Continue' i]",
                    "button[aria-label*='Next' i]",
                    "footer button[data-test-modal-close-btn] + button",  # modal footer save/next
                    "div[data-test-modal-container] button.artdeco-button--primary",
                    "button:has-text('Submit application')",
                    "button:has-text('Review your application')",
                    "button:has-text('Review')",
                    "button:has-text('Continue')",
                    "button:has-text('Next')",
                    "button:has-text('Save & continue')",
                    "button:has-text('Save and continue')",
                    "button:has-text('Save')",
                ]
                cta_clicked_text = ""
                for sel in cta_selectors:
                    try:
                        btn = page.locator(sel).first
                        if not await btn.is_visible(timeout=600):
                            continue
                        # Skip disabled buttons (e.g. validation error on the form)
                        try:
                            disabled = await btn.is_disabled()
                            if disabled:
                                continue
                        except:
                            pass
                        cta_clicked_text = ((await btn.text_content()) or "").strip()
                        await btn.click(timeout=3000)
                        await page.wait_for_timeout(900)
                        navigated = True
                        if "Submit" in cta_clicked_text or "review" in cta_clicked_text.lower():
                            # Was the final submit — wait + confirm
                            await page.wait_for_timeout(1200)
                            if await self._is_submitted(page):
                                try:
                                    await page.click("button:has-text('Done')", timeout=2000)
                                except:
                                    pass
                                print(f"     ✅ LinkedIn Applied: {job['title']} @ {job['company']}")
                                return ApplicationResult(job=job, status="applied")
                        break  # one CTA click per step
                    except Exception:
                        continue

                if not navigated:
                    # Stuck — take screenshot, close modal and skip (don't pollute manual list)
                    try:
                        import datetime
                        stamp = datetime.datetime.now().strftime("%H%M%S")
                        await page.screenshot(path=f"c:/Users/{os.getenv('USERNAME', 'User')}/.jarvis/automations/job-automation/scratch/linkedin_stuck_{stamp}.png")
                    except:
                        pass
                    await self._close_any_modal(page)
                    return ApplicationResult(job=job, status="skipped", reason=f"Stuck at step {step+1} — new field variant, skipped")

            await self._close_any_modal(page)
            return ApplicationResult(job=job, status="manual", reason="Too many form steps")

        except Exception as e:
            return ApplicationResult(job=job, status="error", reason=str(e))

    async def _fill_step(self, page: Page):
        """Auto-fill all known simple fields on the current Easy Apply step."""
        EMAIL    = os.getenv("LINKEDIN_EMAIL", os.getenv("GMAIL_ADDRESS", ""))
        NAME     = os.getenv("USER_FULL_NAME", "User Name")
        NAME_SHORT = os.getenv("USER_SHORT_NAME", "User")

        # ── Phone number (text input) ──────────────────────────────────────────
        sel = "input[id*='phoneNumber-nationalNumber'], input[id*='phoneNumber'], input[name*='phone'], input[placeholder*='hone']"
        try:
            for el in await page.locator(sel).all():
                if await el.is_visible():
                    val = await el.input_value()
                    if not val:
                        await el.fill(PHONE.replace("+91", "").strip())
                    break
        except:
            pass

        # ── Email dropdown (LinkedIn uses <select> for email) ──────────────────
        sel = "select[id*='email'], select[name*='email'], select[aria-label*='mail']"
        try:
            for el in await page.locator(sel).all():
                if await el.is_visible():
                    # Try to select by matching email text
                    opts = await el.locator("option").all()
                    for opt in opts:
                        t = (await opt.text_content() or "").strip().lower()
                        if EMAIL and "@" in t and (EMAIL.lower() in t):
                            v = await opt.get_attribute("value") or ""
                            await el.select_option(v)
                            break
                    else:
                        # Fallback: first valid option
                        for opt in opts:
                            v = (await opt.get_attribute("value") or "").strip()
                            if v and v.lower() not in ["", "0", "select", "none"]:
                                await el.select_option(v)
                                break
                    break
        except:
            pass

        # ── Phone country code dropdown ────────────────────────────────────────
        sel = "select[id*='country'], select[id*='phoneNumber-country'], select[name*='country'], select[aria-label*='country' i]"
        try:
            for el in await page.locator(sel).all():
                if await el.is_visible():
                    opts = await el.locator("option").all()
                    for opt in opts:
                        t  = (await opt.text_content() or "").lower()
                        v  = (await opt.get_attribute("value") or "").lower()
                        # Match India or +91
                        if "india" in t or "+91" in t or v in ["in", "ind", "91", "+91"]:
                            await el.select_option(await opt.get_attribute("value") or "")
                            break
                    break
        except:
            pass

        # ── City / Location text field ─────────────────────────────────────────
        sel = "input[id*='city'], input[id*='location'], input[placeholder*='ity']"
        try:
            for el in await page.locator(sel).all():
                if await el.is_visible():
                    val = await el.input_value()
                    if not val:
                        await el.fill("Greater Noida")
                        await page.wait_for_timeout(600)
                        for sug_sel in [".basic-typeahead__selectable", "[role='option']"]:
                            try:
                                for sug in await page.locator(sug_sel).all():
                                    if await sug.is_visible():
                                        await sug.click()
                                        break
                            except:
                                pass
                    break
        except:
            pass

        # ── Years of experience (number input) ────────────────────────────────
        sel = "input[id*='year'], input[id*='experience']"
        try:
            for el in await page.locator(sel).all():
                if await el.is_visible():
                    val = await el.input_value()
                    if not val or val == "0":
                        await el.fill(YEARS_EXP)
                    break
        except:
            pass

        # ── Name fields (external / third-party forms) ────────────────────────
        sel = "input[placeholder='Name'], input[placeholder='Full Name'], input[placeholder='Your Name'], input[name='name'], input[id*='name'], input[aria-label*='name' i]"
        try:
            for el in await page.locator(sel).all():
                if await el.is_visible():
                    val = await el.input_value()
                    if not val:
                        await el.fill(NAME)
                    break
        except:
            pass

        # ── First name / Last name fields ─────────────────────────────────────
        try:
            for fn in await page.locator("input[name='firstName'], input[id*='firstName'], input[placeholder*='irst']").all():
                if await fn.is_visible():
                    if not await fn.input_value():
                        await fn.fill(NAME_SHORT)
                    break
        except:
            pass
        try:
            for ln in await page.locator("input[name='lastName'], input[id*='lastName'], input[placeholder*='ast']").all():
                if await ln.is_visible():
                    if not await ln.input_value():
                        await ln.fill("Palugulla")
                    break
        except:
            pass

        # ── Email text input (external forms) ─────────────────────────────────
        sel = "input[type='email'], input[placeholder='Email'], input[placeholder*='mail' i], input[name='email'], input[id*='email']"
        try:
            for el in await page.locator(sel).all():
                if await el.is_visible():
                    val = await el.input_value()
                    if not val:
                        await el.fill(EMAIL)
                    break
        except:
            pass

        # ── Phone text input (external forms) ─────────────────────────────────
        sel = "input[placeholder='Phone number'], input[placeholder='Phone Number'], input[placeholder*='hone' i], input[name='phone'], input[type='tel']"
        try:
            for el in await page.locator(sel).all():
                if await el.is_visible():
                    val = await el.input_value()
                    if not val:
                        await el.fill(PHONE)
                    break
        except:
            pass

        # ── Checkbox (agree/verify checkboxes) ───────────────────────────────
        try:
            checkboxes = page.locator("input[type='checkbox']")
            cnt = await checkboxes.count()
            for i in range(cnt):
                cb = checkboxes.nth(i)
                if await cb.is_visible(timeout=400):
                    if not await cb.is_checked():
                        await cb.click()
                        await page.wait_for_timeout(200)
        except:
            pass

        # ── Generic <select> dropdowns ────────────────────────────────────────
        try:
            selects = page.locator("select")
            sc = await selects.count()
            for i in range(sc):
                try:
                    sel_el = selects.nth(i)
                    if not await sel_el.is_visible(timeout=400):
                        continue
                    cur = await sel_el.input_value()
                    if cur and cur.lower() not in ["", "0", "select", "none"]:
                        continue  # already has a value
                    opts = await sel_el.locator("option").all()
                    for opt in opts:
                        v = (await opt.get_attribute("value") or "").strip()
                        t = (await opt.text_content() or "").strip().lower()
                        if v and t not in ["", "0", "select", "none", "please select", "select an option"]:
                            await sel_el.select_option(v)
                            break
                except:
                    continue
        except:
            pass

        # ── Resume / Document selection ───────────────────────────────────────
        try:
            for btn in await page.locator("button[aria-label*='Choose']").all():
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(500)
                    break
        except:
            pass

        # ── Custom Questions Fallback (Years of Exp, Links, etc.) ─────────────
        try:
            for el in await page.locator("input[type='text']").all():
                if await el.is_visible():
                    val = await el.input_value()
                    if not val:
                        lbl = await page.evaluate('(el) => { let l = el.id ? document.querySelector(`label[for="${el.id}"]`) : null; return l ? l.innerText.toLowerCase() : ""; }', el)
                        if "year" in lbl or "experience" in lbl or "ctc" in lbl or "salary" in lbl or "notice" in lbl:
                            await el.fill("0")
                        elif "link" in lbl or "url" in lbl or "portfolio" in lbl or "github" in lbl or "profile" in lbl:
                            await el.fill(os.getenv("USER_GITHUB_URL", "https://github.com/"))
                        else:
                            await el.fill("0")  # Default to 0 for unknown questions
        except:
            pass

        # ── Radio buttons — prefer Yes / true ────────────────────────────────
        try:
            radios = page.locator("input[type='radio']")
            count = await radios.count()
            handled_names: set = set()
            for i in range(count):
                r = radios.nth(i)
                name = (await r.get_attribute("name")) or f"radio_{i}"
                if name in handled_names:
                    continue
                handled_names.add(name)
                group = page.locator(f"input[type='radio'][name='{name}']")
                gc = await group.count()
                selected = False
                for j in range(gc):
                    val = ((await group.nth(j).get_attribute("value")) or "").lower()
                    if val in ["yes", "true", "1", "y"]:
                        if not await group.nth(j).is_checked():
                            await group.nth(j).click()
                        selected = True
                        break
                if not selected and gc > 0:
                    if not await group.nth(0).is_checked():
                        await group.nth(0).click()
        except:
            pass


    async def _is_submitted(self, page: Page) -> bool:
        for sel in [
            ":has-text('application was sent')",
            ":has-text('Application submitted')",
            ":has-text('Your application has been submitted')",
            ".artdeco-inline-feedback--success",
            "[data-test-modal-container] h2:has-text('submitted')",
        ]:
            try:
                if await page.locator(sel).first.is_visible(timeout=500):
                    return True
            except:
                pass
        return False

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        """Used when applying to pre-scraped LinkedIn jobs by URL."""
        await page.goto(job["url"], wait_until="domcontentloaded", timeout=TIMEOUT)
        await page.wait_for_timeout(2000)
        return await self._easy_apply(page, job)
