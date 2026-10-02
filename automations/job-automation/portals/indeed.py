"""
portals/indeed.py — Indeed Easy Apply with persistent session support
- Session via storage_state (managed by auto_applier.py)
- Auto-fills common fields: phone, job title, company, radios, dropdowns
- Handles "Use your Indeed Resume" confirmation step
- Detects already-applied state
"""
from __future__ import annotations
import json
import os
import random
from collections import deque
from pathlib import Path
from playwright.async_api import Page
from .base import BasePortal, ApplicationResult, is_experienced_role

TIMEOUT     = 60_000
SESSION_DIR = Path.home() / ".jarvis" / "automations" / "job-automation" / ".sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


class IndeedPortal(BasePortal):
    name = "Indeed"
    login_url = "https://secure.indeed.com/account/login"

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, page: Page) -> bool:
        try:
            # Test existing session first
            await page.goto("https://in.indeed.com", wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(2500)
            if await self._is_logged_in(page):
                print("  ✅ Indeed: session active — skipping login")
                return True

            print("  🔑 Indeed: logging in")
            await page.goto(self.login_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(2000)

            # ── Try credential login ──────────────────────────────────────────
            auto_ok = False
            for sel in ["input[type='email']", "input[name='__email']", "input[id*='email']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=3000):
                        await el.fill(self.email)
                        await page.wait_for_timeout(500)
                        for submit_sel in ["button[type='submit']", "button:has-text('Continue')"]:
                            try:
                                if await page.locator(submit_sel).first.is_visible(timeout=1000):
                                    await page.locator(submit_sel).first.click()
                                    break
                            except:
                                pass
                        await page.wait_for_timeout(3000)
                        break
                except:
                    continue

            for sel in ["input[type='password']", "input[name='__password']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=3000):
                        await el.fill(self.password)
                        await page.wait_for_timeout(500)
                        await page.click("button[type='submit']")
                        await page.wait_for_timeout(5000)
                        auto_ok = True
                        break
                except:
                    continue

            if await self._is_logged_in(page):
                print("  ✅ Indeed: logged in with credentials")
                return True

            # ── Credential login failed (Google OAuth / CAPTCHA / magic link) ─
            # Give user 120s to log in manually via the open browser window
            print("  ⚠️  Indeed: auto-login failed — please log in manually in the browser now")
            print("  ⏳  Waiting 120 seconds for manual login (use Google Sign-In if needed)...")
            print("      (KEEP this browser window OPEN — closing it aborts the login)")

            # Poll every 5s instead of one massive wait, so a closed window is
            # immediately caught without an ugly Playwright traceback
            ok = False
            for _ in range(24):  # 24 × 5s = 120s
                try:
                    await page.wait_for_timeout(5000)
                    if await self._is_logged_in(page):
                        ok = True
                        break
                except Exception as poll_err:
                    # Likely "Target page, context or browser has been closed"
                    print(f"  ⚠️  Polling stopped — browser closed. ({poll_err!s:.80})")
                    return False

            if ok:
                print("  ✅ Indeed: manually logged in — session saved")
                return True

            print("  ❌ Indeed: login timed out (120s) — could not verify session")
            return False

        except Exception as e:
            err = str(e)
            if "closed" in err.lower():
                print("  ⚠️  Indeed: browser was closed before login completed — aborting cleanly")
                return False
            print(f"  ❌ Indeed login error: {e}")
            return False


    async def _is_logged_in(self, page: Page) -> bool:
        # Must find an actual account/user element — URL check alone is not reliable
        try:
            await page.wait_for_selector(
                ".gnav-LoggedInAccountLink, [data-testid='UserDropdown'], "
                "[data-testid='user-account-profile'], .HamburgerMenu-user, "
                "[aria-label*='Account'], .icl-NavigationLinks a[href*='/profile']",
                timeout=5000
            )
            return True
        except:
            return False

    # ── Search and Apply ──────────────────────────────────────────────────────

    async def search_and_apply(self, page: Page, roles: list, cities: list,
                               daily_limit: int, applied_today: set) -> list:
        """
        Search Indeed for jobs inside the logged-in session and auto-apply.
        Returns list of ApplicationResult objects.
        """
        import datetime, asyncio, random as _random
        results = []
        applied = 0
        today = datetime.date.today().isoformat()

        for role in roles[:4]:
            for city in cities[:3]:
                if applied >= daily_limit:
                    break
                try:
                    # Clean search URL — no vjk= param which can cause redirects
                    url = (
                        f"https://in.indeed.com/jobs"
                        f"?q={role.replace(' ', '+')}"
                        f"&l={city.replace(' ', '+')}"
                        f"&fromage=1&sort=date"
                    )
                    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)

                    # Wait for job cards to load
                    loaded = False
                    for card_sel in [".job_seen_beacon", "[data-jk]", ".tapItem", ".slider_item"]:
                        try:
                            await page.wait_for_selector(card_sel, timeout=8000)
                            loaded = True
                            break
                        except:
                            continue

                    if not loaded:
                        print(f"  ⚠️  Indeed: no cards found at {page.url[:70]}")
                        continue

                    await page.wait_for_timeout(1500)

                    # Extract jobs — use real anchor href to avoid 404s
                    job_data = await page.evaluate("""() => {
                        const seen = new Set();
                        const out  = [];
                        const BASE = 'https://in.indeed.com';

                        // Find top-level job cards
                        const selectors = ['.job_seen_beacon', '.tapItem', '.slider_item', '[data-jk]'];
                        let cards = [];
                        for (const sel of selectors) {
                            const found = Array.from(document.querySelectorAll(sel));
                            if (found.length > 0) { cards = found; break; }
                        }

                        cards.forEach(card => {
                            const jk = card.getAttribute('data-jk') ||
                                       card.querySelector('[data-jk]')?.getAttribute('data-jk');
                            if (!jk || seen.has(jk)) return;
                            seen.add(jk);

                            // Get the real job URL from the title anchor
                            const anchor = card.querySelector(
                                'h2.jobTitle a[href], .jcs-JobTitle a[href], h2 a[href]'
                            );
                            const href = anchor ? anchor.href : null;
                            // href is absolute (browser resolves it), fallback to viewjob
                            const jobUrl = href || (BASE + '/viewjob?jk=' + jk);

                            // Title from anchor span or title attribute
                            const titleEl = card.querySelector(
                                'h2.jobTitle span[title], h2.jobTitle a span, .jcs-JobTitle span'
                            );
                            const title = titleEl
                                ? (titleEl.getAttribute('title') || titleEl.innerText || '').trim()
                                : (anchor ? anchor.innerText.trim() : '');
                            if (!title) return;

                            // Company
                            const compEl = card.querySelector(
                                '[data-testid="company-name"], .companyName, [class*="company"]'
                            );
                            const company = compEl ? compEl.innerText.trim() : 'Unknown';

                            out.push({ jk, title, company, url: jobUrl });
                        });

                        return out.slice(0, 8);
                    }""")

                    print(f"  🔍 Indeed: {len(job_data)} jobs for '{role}' in {city}")

                    queue = deque(job_data)
                    visited = set(jd.get("jk", "").strip() for jd in queue)

                    while queue and applied < daily_limit:
                        jd = queue.popleft()

                        jk      = jd.get("jk", "").strip()
                        title   = jd.get("title", "").strip()
                        company = jd.get("company", "Unknown").strip()
                        href    = jd.get("url", "").strip()

                        if not jk or not title:
                            continue

                        # ── Role relevance filter ────────────────────────────
                        # Indeed India mixes profile recommendations with results;
                        # only proceed if the title contains at least one keyword
                        # from the searched role.
                        role_keywords = [w.lower() for w in role.split()
                                         if len(w) > 3]  # skip short words
                        title_lower = title.lower()
                        if role_keywords and not any(kw in title_lower for kw in role_keywords):
                            print(f"     ⏩ Skipping unrelated: {title}")
                            continue

                        job_id = f"indeed_{jk}"
                        if job_id in applied_today:
                            print(f"     ⏭️  Already applied: {title}")
                            continue
                        
                        if is_experienced_role(title, ""):
                            print(f"     ⏭️  Skipped: Requires experience (not fresher/intern)")
                            continue

                        job = {
                            "id":          job_id,
                            "title":       title,
                            "company":     company,
                            "location":    city,
                            "portal":      "Indeed",
                            "url":         href,
                            "description": "",
                            "scraped_at":  today,
                        }

                        print(f"\n  → {title} @ {company} ({city})")

                        # ── Open a fresh page per job ─────────────────────────
                        # Keeps the main search page alive regardless of what
                        # the apply flow does (navigate, popup, iframe, etc.)
                        apply_page = await page.context.new_page()
                        try:
                            # Pre-visit to extract similar jobs
                            try:
                                await apply_page.goto(href, wait_until="domcontentloaded", timeout=TIMEOUT)
                                await apply_page.wait_for_timeout(2000)
                                similar_jobs = await self.extract_similar_jobs(apply_page, roles, city)
                                new_jobs = 0
                                for s_job in similar_jobs:
                                    s_jk = s_job.get("jk", "").strip()
                                    if s_jk and s_jk not in visited:
                                        visited.add(s_jk)
                                        queue.append(s_job)
                                        new_jobs += 1
                                if new_jobs > 0:
                                    print(f"     🔍 Found {new_jobs} similar jobs on page. Added to queue.")
                            except Exception:
                                pass

                            result = await self.apply_to_job(apply_page, job)
                        except Exception as ex:
                            result = ApplicationResult(job=job, status="error",
                                                       reason=str(ex)[:120])
                        finally:
                            try:
                                await apply_page.close()
                            except:
                                pass

                        results.append(result)
                        if result.status == "applied":
                            applied += 1
                            applied_today.add(job_id)
                        elif result.status == "manual":
                            print(f"     📋 Manual: {result.reason}")
                        elif result.status == "skipped":
                            print(f"     ⏭️  Skipped: {result.reason}")
                        elif result.status == "error":
                            print(f"     ❌ Error: {result.reason}")

                        # Track seen so same job isn't retried in same run
                        applied_today.add(job_id)

                        await page.wait_for_timeout(_random.uniform(2000, 3500))

                    await page.wait_for_timeout(_random.uniform(1000, 2000))

                except Exception as ex:
                    print(f"  ❌ Indeed search [{role}/{city}]: {str(ex)[:80]}")
                    continue

        return results

    # ── Apply ─────────────────────────────────────────────────────────────────

    async def extract_similar_jobs(self, page: Page, roles: list, city: str) -> list:
        similar = []
        try:
            job_data = await page.evaluate("""() => {
                const out = [];
                const BASE = 'https://in.indeed.com';
                const cards = document.querySelectorAll('#relatedJobs .jobsearch-SerpJobCard, .jobsearch-RelatedJobs-list li');
                cards.forEach(card => {
                    const anchor = card.querySelector('a[href*="/rc/clk"], a[href*="/viewjob"]');
                    if (!anchor) return;
                    const href = anchor.href;
                    const jkMatch = href.match(/jk=([a-zA-Z0-9]+)/);
                    const jk = jkMatch ? jkMatch[1] : (card.getAttribute('data-jk') || null);
                    if (!jk) return;

                    const titleEl = card.querySelector('.jobTitle, .title, .jobsearch-RelatedJobs-title');
                    const title = titleEl ? titleEl.innerText.trim() : anchor.innerText.trim();
                    const compEl = card.querySelector('.companyName, .company');
                    const company = compEl ? compEl.innerText.trim() : 'Unknown';

                    out.push({ jk, title, company, url: href || (BASE + '/viewjob?jk=' + jk) });
                });
                return out;
            }""")

            for jd in job_data:
                title = jd.get("title", "")
                role_keywords = [w.lower() for w in roles for w in w.split() if len(w) > 3]
                title_lower = title.lower()
                if role_keywords and not any(kw in title_lower for kw in role_keywords):
                    continue
                similar.append(jd)
        except:
            pass
        return similar

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        try:
            await page.goto(job["url"], wait_until="domcontentloaded", timeout=TIMEOUT)

            # --- Extract Job Description ---
            try:
                desc_el = page.locator("#jobDescriptionText, .jobsearch-JobComponent-description").first
                if await desc_el.is_visible(timeout=2000):
                    job["description"] = (await desc_el.text_content()).strip()
            except:
                pass
            
            if not job.get("description", "").strip():
                job["description"] = job.get("title", "")

            # --- Filter by Experience (with description) ---
            if is_experienced_role(job.get("title", ""), job.get("description", "")):
                return ApplicationResult(job=job, status="skipped", reason="Requires experience (not fresher/intern)")

            # Wait for the Indeed Apply button to render (JS widget)
            apply_sel_found = None
            for sel in [
                ".ia-IndeedApplyButton",
                "[data-testid='indeedApply']",
                "[class*='IndeedApply']",
                "button:has-text('Apply now')",
                "button:has-text('Apply with Indeed')",
                "span.indeed-apply-widget"
            ]:
                try:
                    await page.wait_for_selector(sel, timeout=5000)
                    apply_sel_found = sel
                    break
                except:
                    continue

            if not apply_sel_found:
                return ApplicationResult(
                    job=job, status="skipped",
                    reason="No Indeed Apply button — external company site"
                )

            await page.wait_for_timeout(1000)

            # Primary click: Playwright's force=True bypasses overlay interceptors reliably
            try:
                # If the selector was just the widget container, target its button
                click_sel = apply_sel_found
                if click_sel == "span.indeed-apply-widget":
                    click_sel = "span.indeed-apply-widget button"
                
                await page.locator(click_sel).first.click(force=True, timeout=3000)
            except:
                # Fallback: Broad JS click covering all known Indeed India button classes
                await page.evaluate("""() => {
                    const sels = [
                        '.ia-IndeedApplyButton', '[data-testid="indeedApply"]',
                        '[class*="IndeedApply"]', 'button.indeed-apply-button',
                        'span.indeed-apply-widget button',
                        'button:contains("Apply")'
                    ];
                    for (const s of sels) {
                        try {
                            const el = document.querySelector(s);
                            if (el) { el.click(); return; }
                        } catch(e) {} // ignore invalid selector errors
                    }
                }""")

            await page.wait_for_timeout(2500)

            # ── Detect apply form ─────────────────────────────────────────────
            popup_page = None
            try:
                popup_page = await page.context.wait_for_event("page", timeout=2000)
                await popup_page.wait_for_timeout(2000)
            except:
                pass

            apply_frame = None
            if not popup_page:
                # Poll for up to 8 seconds for the iframe to inject and render
                for _ in range(16):
                    try:
                        iframe_count = await page.locator("iframe").count()
                        for i in range(iframe_count):
                            fl = page.frame_locator("iframe").nth(i)
                            # Does this iframe have a Continue/Apply button or resume text?
                            is_apply_frame = False
                            for check_sel in [
                                "button:has-text('Continue')", 
                                "button:has-text('Apply')", 
                                "button:has-text('Submit')", 
                                "h1:has-text('resume')",
                                "[data-testid*='Continue']"
                            ]:
                                if await fl.locator(check_sel).first.is_visible(timeout=300):
                                    is_apply_frame = True
                                    break
                            if is_apply_frame:
                                apply_frame = fl
                                break
                    except:
                        pass
                    
                    if apply_frame:
                        break
                    await page.wait_for_timeout(500)

            if popup_page:
                def loc(sel): return popup_page.locator(sel).first
                print("     🪟  Indeed: popup apply form")
            elif apply_frame:
                def loc(sel): return apply_frame.locator(sel).first
                print("     🖼️  Indeed: iframe apply form")
            else:
                def loc(sel): return page.locator(sel).first
                print("     📄  Indeed: inline apply form")

            # ── Step 1: Resume confirmation — click the confirm/continue button ──
            # Indeed's first modal screen says "Apply with your Indeed Resume" + button
            confirmed = False
            for btn_txt in ["Continue", "Apply", "Use your Indeed Resume",
                            "Apply with this resume", "Use this resume",
                            "Apply now", "Apply Now", "Submit"]:
                try:
                    btn = loc(f"button:has-text('{btn_txt}'):visible")
                    await btn.wait_for(state="visible", timeout=3000)
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    confirmed = True
                    break
                except:
                    continue
            if not confirmed:
                print("     ⚠️  Indeed: resume confirm step not found — trying to proceed")
                try:
                    await page.screenshot(path="indeed_debug.png", full_page=True)
                except:
                    pass

            # ── Steps 2-N: Fill fields then click Continue / Submit ───────────
            for step in range(8):
                await page.wait_for_timeout(3000)  # wait for step to render

                # Submitted?
                if await self._is_submitted_target_loc(loc):
                    print(f"     ✅ Indeed Applied: {job['title']} @ {job['company']}")
                    if popup_page:
                        try: await popup_page.close()
                        except: pass
                    return ApplicationResult(job=job, status="applied")

                # Fill: job title → Student, company → University, phone
                await self._fill_fields_loc(loc)

                # Submit?
                for sub_txt in ["Submit your application", "Submit application", "Submit"]:
                    try:
                        btn = loc(f"button:has-text('{sub_txt}'):visible")
                        if await btn.is_visible(timeout=1500):
                            await btn.click()
                            await page.wait_for_timeout(5000)
                            print(f"     ✅ Indeed Applied: {job['title']} @ {job['company']}")
                            if popup_page:
                                try: await popup_page.close()
                                except: pass
                            return ApplicationResult(job=job, status="applied")
                    except:
                        continue

                # Continue / Next — use wait_for(visible) which properly waits for React
                navigated = False
                for btn_txt in ["Continue", "Next", "Review your application", "Review"]:
                    try:
                        btn = loc(f"button:has-text('{btn_txt}'):visible")
                        await btn.wait_for(state="visible", timeout=3000)
                        await btn.click()
                        await page.wait_for_timeout(2500)
                        navigated = True
                        break
                    except:
                        continue

                if not navigated:
                    return ApplicationResult(
                        job=job, status="manual",
                        reason=f"Stuck at step {step+1} — apply manually"
                    )

            return ApplicationResult(job=job, status="manual", reason="Too many steps")


        except Exception as e:
            return ApplicationResult(job=job, status="error", reason=str(e))

    async def _close_target(self, target, main_page: Page):
        """Close target if it's a popup Page (not a FrameLocator or main page)."""
        try:
            if hasattr(target, "close") and target != main_page:
                await target.close()
        except:
            pass

    _SUCCESS_SELECTORS = [
        ":has-text('application was sent')",
        ":has-text('Application submitted')",
        ":has-text('Your application has been submitted')",
        ":has-text('successfully applied')",
        ":has-text('Application sent')",
        ".ia-PostApply",
        "[data-testid='applicationConfirmation']",
    ]

    async def _is_submitted_target(self, target) -> bool:
        """Check submission success — works on both Page and FrameLocator."""
        for sel in self._SUCCESS_SELECTORS:
            try:
                if await target.locator(sel).first.is_visible(timeout=500):
                    return True
            except:
                pass
        return False

    async def _is_submitted_target_loc(self, loc) -> bool:
        """Check submission — takes a loc() callable."""
        for sel in self._SUCCESS_SELECTORS:
            try:
                if await loc(sel).is_visible(timeout=500):
                    return True
            except:
                pass
        return False

    async def _build_context(self, el) -> str:
        """Build lowercased context string from aria-label, name, id, and label."""
        ctx_parts = []
        for attr in ["aria-label", "name", "id"]:
            try:
                v = await el.get_attribute(attr) or ""
                ctx_parts.append(v)
            except Exception:
                pass
        try:
            label_text = await el.evaluate("n => n.closest('label') ? n.closest('label').innerText : ''")
            ctx_parts.append(label_text or "")
        except Exception:
            pass
        return " ".join(ctx_parts).lower()

    @staticmethod
    def _resolve_field_value(ctx: str) -> str | None:
        """Given a context string, return the appropriate fill value or None to skip."""
        if "year" in ctx or "experience" in ctx:
            return "0"
        if "expected" in ctx or "desired" in ctx:
            return "400000"
        if "salary" in ctx or "ctc" in ctx or "pay" in ctx:
            return "0" 
        if "bachelor" in ctx or "undergraduate" in ctx or "ug" in ctx:
            return "BSc"
        if "master" in ctx or "postgraduate" in ctx or "pg" in ctx:
            return "MCA"
        if "degree" in ctx or "education" in ctx or "qualification" in ctx:
            return "MCA" 
        if "skill" in ctx or "technology" in ctx or "tools" in ctx:
            return "Python, Django, Machine Learning, React, JavaScript"
        if "notice" in ctx or "join" in ctx:
            return "15"
        if "name" in ctx and "company" not in ctx:
            return None  # skip
        if "link" in ctx or "url" in ctx or "portfolio" in ctx or "website" in ctx:
            return os.getenv("USER_GITHUB_URL", "https://github.com/")
        return None

    async def _fill_field_single(self, loc, selectors: list[str], value: str) -> bool:
        """Find a visible element by one of the selectors and fill it if empty."""
        for sel in selectors:
            try:
                el = loc(sel)
                if await el.is_visible(timeout=400):
                    cur = await el.input_value()
                    if not cur:
                        await el.fill(value)
                    return True
            except:
                continue
        return False

    async def _fill_text_inputs(self, loc):
        """Smart fill for text/number inputs based on label context."""
        try:
            inputs = loc("input[type='text'], input[type='number']")
            ic = await inputs.count()
            for i in range(ic):
                el = inputs.nth(i)
                if not await el.is_visible(timeout=200):
                    continue
                val = await el.input_value()
                if val:
                    continue
                ctx = await self._build_context(el)
                resolved = self._resolve_field_value(ctx)
                if resolved is not None:
                    await el.fill(resolved)
        except Exception:
            pass

    async def _fill_radios(self, loc):
        """Check radio groups — prefer Yes, fallback to first option."""
        try:
            radios = loc("input[type='radio']")
            count = await radios.count()
            seen: set = set()
            for i in range(count):
                r = radios.nth(i)
                name = (await r.get_attribute("name")) or f"r{i}"
                if name in seen:
                    continue
                seen.add(name)
                group = []
                has_checked = False
                for j in range(count):
                    rv = radios.nth(j)
                    if (await rv.get_attribute("name")) == name:
                        group.append(rv)
                        if await rv.is_checked():
                            has_checked = True
                if has_checked or not group:
                    continue
                clicked = False
                for rv in group:
                    val = str(await rv.get_attribute("value")).lower()
                    label_text = ""
                    try:
                        label_text = str(await rv.evaluate(
                            "n => n.closest('label') ? n.closest('label').innerText : ''"
                        )).lower()
                    except Exception:
                        pass
                    if val in ["yes", "true", "1", "y"] or "yes" in label_text:
                        await rv.click(force=True)
                        clicked = True
                        break
                if not clicked:
                    await group[0].click(force=True)
        except Exception:
            pass

    async def _fill_checkboxes(self, loc):
        """Check unchecked checkboxes."""
        try:
            checkboxes = loc("input[type='checkbox']")
            cc = await checkboxes.count()
            for i in range(cc):
                cb = checkboxes.nth(i)
                if await cb.is_visible(timeout=200) and not await cb.is_checked():
                    await cb.click(force=True)
        except Exception:
            pass

    async def _fill_dropdowns(self, loc):
        """Fill select dropdowns with first non-empty option."""
        try:
            selects = loc("select")
            sc = await selects.count()
            for i in range(sc):
                sel_el = selects.nth(i)
                if not await sel_el.is_visible(timeout=300):
                    continue
                opts = await sel_el.locator("option").all()
                for opt in opts:
                    v = (await opt.get_attribute("value")) or ""
                    if v and v.lower() not in ["", "0", "select", "none", "please select"]:
                        await sel_el.select_option(v)
                        break
        except Exception:
            pass

    async def _fill_fields_loc(self, loc):
        """Fill form fields — takes a loc() callable (works for Frame/Page/popup)."""
        await self._fill_field_single(loc, [
            "input[id*='jobTitle']", "input[placeholder*='Job title' i]",
            "input[aria-label*='job title' i]", "input[name*='jobTitle']"
        ], "Student")

        await self._fill_field_single(loc, [
            "input[id*='company']", "input[placeholder*='Company' i]",
            "input[id*='employer']", "input[aria-label*='company' i]", "input[name*='company']"
        ], os.getenv("USER_UNIVERSITY", "Your University"))

        await self._fill_field_single(loc, [
            "input[type='tel']", "input[id*='phone']", "input[name*='phone']",
            "input[placeholder*='hone' i]"
        ], os.getenv("USER_PHONE", "+910000000000"))

        await self._fill_text_inputs(loc)
        await self._fill_radios(loc)
        await self._fill_checkboxes(loc)
        await self._fill_dropdowns(loc)


    # ── Field filling ─────────────────────────────────────────────────────────

    async def _fill_fields(self, p: Page):
        """Fill form fields on a Page directly (delegates to loc-based helpers)."""
        def loc(sel): return p.locator(sel).first
        await self._fill_fields_loc(loc)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _is_submitted(self, p: Page) -> bool:
        return await self._is_submitted_target(p)
