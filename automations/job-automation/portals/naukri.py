"""
portals/naukri.py — Naukri Quick Apply with persistent session support
- Session is managed by auto_applier.py via storage_state
- Only re-logins if session expired
- Uses Naukri Quick Apply (portal's default resume/profile)
- search_jobs() finds jobs via Playwright (bypasses anti-scrape)
"""
import random
import asyncio
import datetime
import hashlib
from typing import Optional
from playwright.async_api import Page
from .base import (
    BasePortal,
    ApplicationResult,
    is_experienced_role,
    NAME,
    FIRST_NAME,
    LAST_NAME,
    EMAIL,
    PHONE_DIGITS,
)

TIMEOUT = 60_000

ROLES = [
    "Python Developer",
    "Django Developer",
    "Backend Developer",
    "Full Stack Python Developer",
    "Full Stack Developer",
    "Full Stack AI Engineer",
    "AI ML Engineer",
    "Machine Learning Engineer",
    "AI Engineer",
    "Deep Learning Engineer",
    "Android Developer",
    "Java Developer",
    "Software Engineer",
    "SDE",
    "Software Development Engineer",
]
CITIES = ["Gurugram", "Noida", "Greater Noida", "Delhi", "Hyderabad", "Bangalore"]


class NaukriPortal(BasePortal):
    name = "Naukri"
    base_url = "https://www.naukri.com"

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, page: Page) -> bool:
        try:
            await page.goto("https://www.naukri.com", wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(3000)

            # Check if already logged in (session restored from storage_state)
            if await self._is_logged_in(page):
                print("  ✅ Naukri: session active — skipping login")
                return True

            # Click Login button
            for sel in ["a:has-text('Login')", ".nI-gNb-lg__sec a:has-text('Login')", "[title='Login']"]:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue

            # Fill email
            for sel in ["input[type='text']", "input[type='email']", "#usernameField", "input[name='username']", "input[placeholder*='mail']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=3000):
                        await el.fill(self.email)
                        await page.wait_for_timeout(400)
                        break
                except:
                    continue

            # Fill password
            for sel in ["input[type='password']", "#passwordField", "input[placeholder*='assword']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.fill(self.password)
                        await page.wait_for_timeout(400)
                        break
                except:
                    continue

            await page.keyboard.press("Enter")
            await page.wait_for_timeout(5000)

            if await self._is_logged_in(page):
                print("  ✅ Naukri: logged in")
                return True

            await page.screenshot(path="naukri_headless_error.png", full_page=True)
            print("  ❌ Naukri: login failed — check credentials in .env (saved screenshot to naukri_headless_error.png)")
            return False

        except Exception as e:
            print(f"  ❌ Naukri login error: {e}")
            return False

    async def _is_logged_in(self, page: Page) -> bool:
        try:
            await page.wait_for_selector(
                ".nI-gNb-drawer__bars, .user-name, .nI-gNb-lg__sec--login, [class*='loggedIn']",
                timeout=4000
            )
            return True
        except:
            return "mnjuser" in page.url or "homepage" in page.url

    # ── Playwright-based job search (bypasses anti-scrape) ────────────────────

    async def search_and_apply(self, page: Page, roles: list, cities: list, daily_limit: int,
                                applied_today: set, context=None, job_filter=None) -> list:
        """
        Search Naukri for fresh jobs via Playwright after login.
        Returns list of ApplicationResult objects.
        If the page dies during application, a new page is created from context.
        """
        results = []
        applied = 0
        today = datetime.date.today().isoformat()
        limit_hit = False

        for role in roles:
            if limit_hit:
                break
            for city in cities:
                if applied >= daily_limit:
                    limit_hit = True
                    break
                try:
                    # Check if page is still alive; recreate if dead
                    try:
                        _ = page.url
                    except:
                        if context:
                            print("  🔄 Page died — creating new page to continue...")
                            page = await context.new_page()
                        else:
                            print("  ❌ Page died and no context available — stopping")
                            return results

                    query = role.replace(" ", "%20")
                    loc   = city.replace(" ", "-").lower()
                    url   = (
                        f"https://www.naukri.com/{role.replace(' ','-').lower()}"
                        f"-jobs-in-{loc}?experience=0&jobAge=7"
                    )
                    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
                    await page.wait_for_timeout(3000)

                    # Extract ALL job data at once via JS — avoids stale locator timeout
                    job_data = await page.evaluate("""() => {
                        const cards = document.querySelectorAll(
                            '.srp-jobtuple-wrapper, .jobTuple, article.jobTuple'
                        );
                        const results = [];
                        cards.forEach(card => {
                            const titleEl  = card.querySelector('a.title, h2.title a, .jobTitle a');
                            const compEl   = card.querySelector('.comp-name, .companyInfo a, .company-name');
                            if (!titleEl) return;
                            results.push({
                                href:    titleEl.href  || '',
                                title:   titleEl.innerText.trim(),
                                company: compEl ? compEl.innerText.trim() : 'Unknown',
                            });
                        });
                        return results.slice(0, 8);
                    }""")

                    print(f"  🔍 Naukri: {len(job_data)} jobs for '{role}' in {city}")

                    for jd in job_data:
                        if applied >= daily_limit:
                            break

                        href    = jd.get("href", "").strip()
                        title   = jd.get("title", "").strip()
                        company = jd.get("company", "Unknown").strip()

                        if not href or not title:
                            continue

                        job_id = f"naukri_{hashlib.sha256(href.encode()).hexdigest()[:10]}"
                        if job_id in applied_today:
                            print(f"     ⏭️  Already applied: {title}")
                            continue

                        job = {
                            "id":          job_id,
                            "title":       title,
                            "company":     company,
                            "location":    city,
                            "portal":      "Naukri",
                            "url":         href,
                            "description": "",
                            "scraped_at":  today,
                        }

                        print(f"\n  → {title} @ {company} ({city})")
                        if job_filter is not None and not await job_filter(job):
                            print(f"     ⏭️  Skipped: LLM fit filter rejected")
                            continue
                        try:
                            result = await self.apply_to_job(page, job)
                            results.append(result)

                            if result.status == "applied":
                                applied += 1
                                applied_today.add(job_id)
                            elif result.status == "manual":
                                print(f"     📋 Manual: {result.reason}")
                            elif result.status == "skipped":
                                print(f"     ⏭️  Skipped: {result.reason}")
                        except Exception as ex:
                            print(f"     ⚠️  Apply error: {str(ex)[:80]}")

                        # Recover page if it died during apply
                        try:
                            _ = page.url
                        except:
                            if context:
                                print("  🔄 Page died after apply — creating new page...")
                                page = await context.new_page()

                        await asyncio.sleep(random.uniform(3, 5))

                    await asyncio.sleep(random.uniform(2, 4))

                except Exception as ex:
                    print(f"  ❌ Naukri search [{role}/{city}]: {str(ex)[:80]}")
                    # Try to recover page for the next iteration
                    try:
                        _ = page.url
                    except:
                        if context:
                            print("  🔄 Page died — creating new page to continue...")
                            page = await context.new_page()
                    continue

        return results

    async def _get_chatbot_question(self, page: Page) -> str:
        try:
            return await page.evaluate("""() => {
                const container = document.querySelector("[class*='chat'], [class*='drawer'], [class*='chatbot'], [class*='panel']");
                if (!container) return "";
                const bubbles = Array.from(container.querySelectorAll("div, span, p, .msg, .message, .bubble"));
                for (let i = bubbles.length - 1; i >= 0; i--) {
                    const el = bubbles[i];
                    if (el.children.length > 0) continue;
                    const text = el.innerText ? el.innerText.trim() : "";
                    if (text.length > 10 && text.length < 300) {
                        if (text.includes("?") || 
                            text.toLowerCase().includes("experience") || 
                            text.toLowerCase().includes("notice") || 
                            text.toLowerCase().includes("ctc") || 
                            text.toLowerCase().includes("salary") || 
                            text.toLowerCase().includes("location")) {
                            return text;
                        }
                    }
                }
                return "";
            }""")
        except:
            return ""

    def _resolve_chatbot_answer(self, question: str) -> Optional[str]:
        """Resolve a free-text chatbot question to a typed answer.

        Returns None when the question can't be confidently answered. The
        caller must NOT type anything then — it marks the job manual. Never
        default unknown questions to a canned "Yes": the old fallback typed
        "Yes" into name/email/phone fields and submitted invalid applications.
        """
        q = (question or "").strip().lower()
        if not q:
            return None

        # ── Identity / contact — NEVER free-text a canned reply here ──────────
        if any(k in q for k in ["full name", "your name", "what is your name",
                                "enter your name", "candidate name"]):
            return NAME
        if "first name" in q:
            return FIRST_NAME
        if "last name" in q:
            return LAST_NAME
        if "email" in q or "mail id" in q or "email address" in q:
            return EMAIL
        if "phone" in q or "mobile" in q or "contact number" in q or "phone number" in q:
            return PHONE_DIGITS
        if "current location" in q or "current city" in q or "currently located" in q or "current address" in q:
            return "Delhi"

        if "gender" in q or "sex" in q:
            return "Male"
        elif "dob" in q or "date of birth" in q or "birth date" in q or "birthday" in q:
            return "08/04/2002"
        elif "year of passing" in q or "passing year" in q or "graduation year" in q or "passed out" in q:
            if "10th" in q or "ssc" in q:
                return "2019"
            elif "12th" in q or "intermediate" in q or "hsc" in q:
                return "2019"
            elif "bachelor" in q or "bsc" in q or "bca" in q or "b.tech" in q:
                return "2022"
            return "2026"  # MCA (current)
        elif "arrear" in q or "backlog" in q or "atkt" in q or "supplementary" in q:
            return "No"
        elif "cgpa" in q or "gpa" in q or "percentage" in q or "marks" in q or "score" in q:
            if "10th" in q or "12th" in q or "bachelor" in q:
                return "85"
            return "8.35"
        elif "experience" in q or "exp " in q or ("years of" in q and "passing" not in q) or ("year of" in q and "passing" not in q) or "how many year" in q:
            # Yes/no skill question ("do you have experience with X") — answer
            # from the resume. A years-count question gets the fresher answer.
            if ("do you have" in q or "have you" in q) and self._has_resume_skill(q):
                return "Yes"
            return "0"
        elif q.strip() == "age" or "your age" in q or "what is your age" in q or ("age" in q and "experience" not in q and "agent" not in q and "package" not in q):
            return "24"
        elif "ctc" in q or "salary" in q or "lpa" in q or "income" in q or "compensation" in q or "package" in q or "variable" in q or "pay" in q or "lac" in q or "lakh" in q:
            if "expected" in q or "desired" in q:
                if "lac" in q or "lakh" in q or "lpa" in q:
                    return "6"
                return "600000"
            if "lac" in q or "lakh" in q or "lpa" in q:
                return "1"
            return "0"
        elif "notice" in q or "join" in q or "serving" in q:
            if "immediate" in q or "days" in q or "month" in q:
                return "Immediate"
            return "15 days"
        elif "degree" in q or "qualification" in q or "education" in q or "college" in q or "university" in q:
            return "MCA"
        elif "skill" in q or "proficien" in q or "familiar" in q or "knowledge" in q or "know" in q:
            # Check if the question mentions a skill from the resume
            if self._has_resume_skill(q):
                return "Yes"
            return "No"
        elif "python" in q or "django" in q or "react" in q or "javascript" in q or "mysql" in q:
            if self._has_resume_skill(q):
                return "Yes"
            return "No"
        # Work history — fresher, never worked before
        elif any(k in q for k in ["worked before", "currently working", "currently employed",
                                    "are you working", "do you work", "have you worked",
                                    "previous employer", "previous company", "last company",
                                    "employed currently", "presently working"]):
            return "No"
        # Genuine yes/no intent. Excludes "why do you"/"what do you"/"how do you"
        # leads — those are open questions and must not get a canned "Yes".
        elif ("are you" in q or "would you" in q or "can you" in q
              or "willing" in q or "agree" in q or "accept" in q
              or "interested in" in q or "ready to" in q
              or "open to" in q or "ok for you" in q):
            return "Yes"
        # Unhandled/free-text question (why this role, describe a project, …).
        # No confident answer — caller marks the job manual instead of typing "Yes".
        return None

    # Skills from resume — used for accurate skill-based answers
    RESUME_SKILLS = [
        # Backend & API
        "python", "django", "drf", "django rest framework", "rest", "restful", "api",
        "backend", "server", "web development",
        # Frontend
        "react", "reactjs", "react.js", "javascript", "js", "html", "html5",
        "css", "css3", "bootstrap", "responsive", "frontend", "front end", "front-end",
        # Database
        "mysql", "sql", "database", "db", "orm", "query", "schema",
        # ML / AI
        "machine learning", "ml", "ai", "artificial intelligence", "deep learning",
        "tensorflow", "scikit-learn", "sklearn", "cnn", "neural network",
        "model training", "feature engineering", "data science",
        # Programming fundamentals
        "java", "oops", "oop", "object oriented", "data structure", "algorithm", "dsa",
        # General
        "git", "github", "full stack", "fullstack", "full-stack", "software development",
        "agile", "problem solving", "debugging",
    ]

    def _has_resume_skill(self, text: str) -> bool:
        """Check if the given text mentions any skill from the resume."""
        t = text.lower()
        for skill in self.RESUME_SKILLS:
            if skill in t:
                return True
        return False

    def _resolve_option_for_question(self, question: str, options: list) -> dict:
        """Context-aware option resolver: picks the right radio/checkbox option based on the question."""
        q = question.lower()

        def find_opt(target_texts):
            for target in target_texts:
                for opt in options:
                    txt = opt["text"].lower().strip()
                    if target == txt or target in txt:
                        return opt
            return None

        # Questions that should be answered "No"
        if any(k in q for k in ["current employee", "currently working", "employed with",
                                 "employed by", "internal candidate", "worked before",
                                 "have you worked", "are you working", "do you work",
                                 "currently employed", "presently working"]):
            opt = find_opt(["no"])
            if opt:
                return opt

        if any(k in q for k in ["applied within", "applied in", "applied before",
                                 "applied to", "applied for this"]):
            opt = find_opt(["no"])
            if opt:
                return opt

        if any(k in q for k in ["criminal", "convicted", "terminated", "disciplinary", "felony"]):
            opt = find_opt(["no"])
            if opt:
                return opt

        if any(k in q for k in ["sponsorship", "visa", "require sponsorship"]):
            if "require" in q:
                opt = find_opt(["no"])
                if opt:
                    return opt

        # Notice Period
        if any(k in q for k in ["notice", "join", "serving", "how soon"]):
            opt = find_opt(["immediate", "15 days", "30 days", "1 month", "serving notice"])
            if opt:
                return opt

        # Education / Degree
        if any(k in q for k in ["degree", "qualification", "education", "highest study",
                                 "college", "choose the degree"]):
            opt = find_opt(["mca", "b.tech", "btech", "b. tech", "bachelor", "master",
                            "graduate", "post graduate"])
            if opt:
                return opt

        # Gender
        if any(k in q for k in ["gender", "sex", "male or female", "male/female"]):
            opt = find_opt(["male", "m"])
            if opt:
                return opt

        # Pronouns
        if any(k in q for k in ["pronoun", "preferred pronoun"]):
            opt = find_opt(["he/him", "he/him/his", "he"])
            if opt:
                return opt

        # Relocation / Willingness
        if any(k in q for k in ["relocate", "willing", "ready to", "open to work", "open to"]):
            opt = find_opt(["yes"])
            if opt:
                return opt

        # Skill-based options: only select skills that match the resume
        if any(k in q for k in ["skill", "technology", "proficien", "familiar", "knowledge",
                                 "select", "choose", "pick", "which of"]):
            # Filter options to only those matching resume skills
            matching = [opt for opt in options if self._has_resume_skill(opt["text"].lower())]
            if matching:
                print(f"     🎯 Resume-matched skills: {[m['text'] for m in matching]}")
                return matching[0]
            # If no match, still pick the first option as fallback
            return options[0] if options else None

        # Check if options themselves look like skill/technology names
        # (e.g. ['.Net', 'react JS', 'C#', 'ASP.NET'])
        skill_like = sum(1 for o in options if any(c in o["text"].lower() for c in 
                         ["python", "java", "react", "django", ".net", "sql", "c#", "angular",
                          "node", "php", "ruby", "go", "rust", "swift", "kotlin", "html", "css",
                          "js", "typescript", "aws", "azure", "docker", "kubernetes"]))
        if skill_like >= 2:  # Most options look like tech skills
            matching = [opt for opt in options if self._has_resume_skill(opt["text"].lower())]
            if matching:
                print(f"     🎯 Resume-matched skills: {[m['text'] for m in matching]}")
                return matching[0]

        # General preference fallback
        prefs = [
            "mca", "b.tech", "btech", "b. tech", "bachelor's", "master's",
            "graduate", "post graduate", "immediate", "15 days", "30 days",
            "yes", "agree", "accept", "willing"
        ]
        opt = find_opt(prefs)
        if opt:
            return opt

        # Last resort: return None so we can trigger Vision AI fallback
        return None

    async def _get_drawer_question(self, container) -> str:
        """Extract the most recent question text from the chatbot drawer."""
        try:
            return await container.evaluate("""(el) => {
                // Look for bot message elements (Naukri uses .botMsg, .chatbot_ListItem)
                const msgs = Array.from(el.querySelectorAll(
                    ".botMsg, .chatbot_ListItem, [class*='botMsg'], [class*='ListItem'], .msg, .message, .bubble, p, span"
                ));
                // Texts to ignore (UI elements, not questions)
                const ignoreTexts = ['skip this question', 'save', 'submit', 'continue', 'apply', 
                                     'send', 'cancel', 'close', 'back', 'next', 'type message here'];
                // Walk backwards to find the most recent question-like leaf text
                for (let i = msgs.length - 1; i >= 0; i--) {
                    const m = msgs[i];
                    const text = (m.innerText || "").trim();
                    const textLower = text.toLowerCase();
                    // Must be a leaf or short text, and look like a question/prompt
                    if (text.length > 5 && text.length < 300 && !text.includes("\\n")) {
                        // Skip UI elements and non-question texts
                        if (ignoreTexts.some(t => textLower === t)) continue;
                        return text;
                    }
                }
                return "";
            }""")
        except:
            return ""

    # ── Apply ─────────────────────────────────────────────────────────────────

    async def apply_to_job(self, page: Page, job: dict) -> ApplicationResult:
        try:
            await page.goto(job["url"], wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(random.uniform(2000, 3500))

            # --- Extract Job Description ---
            try:
                desc_el = page.locator(".danger-html, section.job-desc").first
                if await desc_el.is_visible(timeout=1000):
                    job["description"] = (await desc_el.text_content()).strip()
            except:
                pass

            # Already applied?
            for sel in ["button:has-text('Applied')", ".already-applied", "[class*='alreadyApplied']"]:
                try:
                    if await page.locator(sel).first.is_visible(timeout=1500):
                        return ApplicationResult(job=job, status="skipped", reason="Already applied")
                except:
                    pass

            # Find Quick Apply / Apply button
            apply_btn = None
            for sel in [
                "button:has-text('Quick Apply')",
                "button:has-text('Apply')",
                ".apply-button button",
                "#apply-button",
                "[class*='applyBtn']",
                "[id*='apply']",
                "button[id*='apply']",
                "a:has-text('Apply Now')",
            ]:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        btn_text = (await btn.text_content() or "").lower()
                        # If the button says 'apply on company website', skip this job entirely
                        if "company" in btn_text or "website" in btn_text or "external" in btn_text:
                            return ApplicationResult(job=job, status="skipped", reason="External company site apply — skipped")
                        
                        # Check if it's a link to an external site
                        href = await btn.get_attribute("href")
                        if href and href != "#" and "javascript" not in href and "naukri.com" not in href and href.startswith("http"):
                            return ApplicationResult(job=job, status="skipped", reason="External company site apply — skipped")

                        apply_btn = btn
                        break
                except:
                    continue

            if apply_btn is None:
                # ── JS Fallback for Apply Button ──
                try:
                    js_clicked = await page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('button, a, [role="button"], div, span'));
                        for (const b of btns) {
                            const t = (b.innerText || '').trim().toLowerCase();
                            if (t === 'apply' || t === 'quick apply' || t === 'apply now') {
                                b.click();
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if js_clicked:
                        print("  [JS Fallback] Clicked Apply button via JS")
                        apply_btn = True
                        await page.wait_for_timeout(2500)
                except:
                    pass

            if apply_btn is None:
                print("  [Vision Fallback] Attempting to click Apply using AI Vision...")
                try:
                    from shared_dom_llm import solve_with_dom_async
                    await solve_with_dom_async(page, "Click the Apply or Quick Apply button.")
                    await page.wait_for_timeout(2500)
                    apply_btn = True
                except Exception as fe:
                    print(f"  ⚠️  Vision fallback failed: {fe}")
                    return ApplicationResult(job=job, status="skipped", reason="No Apply button found")
            elif apply_btn is not True:
                await apply_btn.click()
                await page.wait_for_timeout(2500)

            # Early success check — some jobs apply directly without a form
            try:
                _ = page.url
            except:
                print(f"     ✅ Naukri Applied (page closed): {job['title']} @ {job['company']}")
                return ApplicationResult(job=job, status="applied")
            if await self._is_applied(page):
                print(f"     ✅ Naukri Applied: {job['title']} @ {job['company']}")
                return ApplicationResult(job=job, status="applied")

            # If redirected to external site, skip it (user only wants portal-native applies)
            if "naukri.com" not in page.url:
                return ApplicationResult(job=job, status="skipped", reason="External form — skipped")

            # Handle popup / modal
            no_container_count = 0
            for step in range(12):
                await page.wait_for_timeout(1500)

                # Gracefully handle page-closed errors (e.g. after successful apply)
                try:
                    _ = page.url  # quick check if page is still alive
                except:
                    print(f"     ✅ Naukri Applied (page closed): {job['title']} @ {job['company']}")
                    return ApplicationResult(job=job, status="applied")

                # Check for success
                if await self._is_applied(page):
                    print(f"     ✅ Naukri Applied: {job['title']} @ {job['company']}")
                    return ApplicationResult(job=job, status="applied")

                # If redirected to external site mid-flow, skip
                if "naukri.com" not in page.url:
                    return ApplicationResult(job=job, status="skipped", reason="External form — skipped")

                # Detect redirect to search/listing page (apply was instant or failed)
                current_url = page.url
                if step == 0 and ("jobs-in-india" in current_url or "/job-listings" not in current_url):
                    # Page redirected away from job listing after clicking Apply
                    if await self._is_applied(page):
                        print(f"     ✅ Naukri Applied: {job['title']} @ {job['company']}")
                        return ApplicationResult(job=job, status="applied")
                    # /myapply/saveApply?strJobsarr=[…] is Naukri's standard
                    # Quick-Apply POST redirect: profile-based submission went
                    # through with no questionnaire form to fill.
                    if "saveApply" in current_url:
                        print(f"     ✅ Naukri Applied (saveApply redirect): {job['title']} @ {job['company']}")
                        return ApplicationResult(job=job, status="applied")
                    # Redirected but no success message — was likely already applied or external
                    print(f"     ⏭️  Redirected after apply: {current_url[:60]}")
                    return ApplicationResult(job=job, status="skipped", reason="Redirected after apply")

                # Find the active container (modal, drawer, chatbot panel)
                # NOTE: selectors ordered from most specific to least; avoid overly broad matches
                container = None
                matched_sel = None
                for sel in [
                    ".chatbot_Drawer",
                    "[class*='chatbot_Drawer']",
                    "[class*='chatbot_DrawerContentWrapper']",
                    "[class*='chatbot']",
                    ".chatbot-container",
                    "[class*='Drawer']:not([class*='gNb'])",
                    "[class*='drawer']:not([class*='gNb'])",
                    "[class*='modal']", "[class*='popup']", "[class*='dialog']",
                    ".side-panel",
                    "[class*='slideOut']", ".layerWrapper", ".modal-content", "[class*='drawer-content']"
                ]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible(timeout=300):
                            # Validate: container must be large enough to be a form (not a tiny nav icon)
                            try:
                                box = await el.bounding_box()
                                if box and box['width'] > 200 and box['height'] > 150:
                                    container = el
                                    matched_sel = sel
                                    break
                            except:
                                continue
                    except:
                        continue

                if container is None:
                    no_container_count += 1
                    if no_container_count >= 3:
                        # No container found after 3 attempts — no form to fill
                        break
                    continue

                if step == 0:
                    print(f"     🔍 Container matched: {matched_sel}")

                # Now we have a container! Restrict all operations to inside the container

                # 1. Chatbot input check — use JS to find and fill the input directly
                # This handles regular inputs, contenteditable divs, and any unusual elements
                try:
                    # Get the question from the drawer first
                    drawer_question = await self._get_drawer_question(container)
                    if not drawer_question:
                        drawer_question = await self._get_chatbot_question(page)
                    
                    # First: check if there are DD/MM/YYYY split date fields and fill them
                    date_filled = await container.evaluate("""(el) => {
                        const inputs = el.querySelectorAll('input');
                        const placeholders = [];
                        for (const inp of inputs) {
                            const rect = inp.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                placeholders.push((inp.placeholder || '').trim().toUpperCase());
                            }
                        }
                        // Check if we have DD/MM/YYYY pattern
                        const hasDD = placeholders.includes('DD');
                        const hasMM = placeholders.includes('MM');
                        const hasYYYY = placeholders.includes('YYYY') || placeholders.includes('YY');
                        
                        if (hasDD || hasMM || hasYYYY) {
                            const nativeSetter = Object.getOwnPropertyDescriptor(
                                window.HTMLInputElement.prototype, 'value'
                            ).set;
                            for (const inp of inputs) {
                                const rect = inp.getBoundingClientRect();
                                if (rect.width <= 0 || rect.height <= 0) continue;
                                const ph = (inp.placeholder || '').trim().toUpperCase();
                                let val = '';
                                if (ph === 'DD') val = '08';
                                else if (ph === 'MM') val = '04';
                                else if (ph === 'YYYY' || ph === 'YY') val = '2002';
                                
                                if (val) {
                                    inp.focus();
                                    nativeSetter.call(inp, val);
                                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                            }
                            return true;
                        }
                        return false;
                    }""")
                    
                    if date_filled:
                        print(f"     📅 Filled DOB fields: DD=08, MM=04, YYYY=2002")
                        await page.wait_for_timeout(500)
                        # Don't press Enter — let the Save button handle it
                        # Fall through to save button click below
                    else:
                        # Use JS to check if there's any typeable input in the drawer
                        has_input = await container.evaluate("""(el) => {
                            // Check for regular inputs (skip date fields)
                            const inputs = el.querySelectorAll('input, textarea');
                            for (const inp of inputs) {
                                const type = (inp.type || 'text').toLowerCase();
                                if (['hidden', 'radio', 'checkbox', 'file', 'submit', 'button'].includes(type)) continue;
                                const ph = (inp.placeholder || '').trim().toUpperCase();
                                if (['DD', 'MM', 'YYYY', 'YY'].includes(ph)) continue;
                                const rect = inp.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    return {found: true, type: 'input', tag: inp.tagName, inputType: type, placeholder: inp.placeholder || ''};
                                }
                            }
                            // Check for contenteditable elements
                            const editables = el.querySelectorAll('[contenteditable="true"], [contenteditable]');
                            for (const ce of editables) {
                                const rect = ce.getBoundingClientRect();
                                if (rect.width > 30 && rect.height > 10) {
                                    return {found: true, type: 'contenteditable', tag: ce.tagName, placeholder: ce.getAttribute('data-placeholder') || ce.getAttribute('placeholder') || ''};
                                }
                            }
                            return {found: false};
                        }""")
                        
                        if has_input.get("found"):
                            answer = self._resolve_chatbot_answer(drawer_question or "")
                            print(f"     🤖 Chatbot input found ({has_input.get('type')}: {has_input.get('tag')}, placeholder='{has_input.get('placeholder', '')}')")
                            print(f"       Q: '{drawer_question}' -> A: '{answer}'")

                            # Fail-safe: never type a canned guess into an
                            # unhandled question — the job goes to the manual
                            # queue where a human applies with a tailored resume.
                            if answer is None:
                                print(f"     ⚠️  Cannot confidently answer '{drawer_question}' — marking manual")
                                return ApplicationResult(
                                    job=job, status="manual",
                                    reason=f"Cannot answer chatbot question: {(drawer_question or '')[:60]}"
                                )

                            if has_input.get("type") == "contenteditable":
                                # Click the contenteditable, clear it, type the answer
                                ce = container.locator("[contenteditable='true'], [contenteditable]").first
                                await ce.click()
                                await page.wait_for_timeout(200)
                                await page.keyboard.press("Control+a")
                                await page.keyboard.type(answer)
                                await page.wait_for_timeout(300)
                                await page.keyboard.press("Enter")
                            else:
                                # Regular input — use JS to set value and dispatch events
                                await container.evaluate("""(el, answer) => {
                                    const inputs = el.querySelectorAll('input, textarea');
                                    for (const inp of inputs) {
                                        const type = (inp.type || 'text').toLowerCase();
                                        if (['hidden', 'radio', 'checkbox', 'file', 'submit', 'button'].includes(type)) continue;
                                        const ph = (inp.placeholder || '').trim().toUpperCase();
                                        if (['DD', 'MM', 'YYYY', 'YY'].includes(ph)) continue;
                                        const rect = inp.getBoundingClientRect();
                                        if (rect.width > 0 && rect.height > 0) {
                                            inp.focus();
                                            const nativeSetter = Object.getOwnPropertyDescriptor(
                                                window.HTMLInputElement.prototype, 'value'
                                            ).set;
                                            nativeSetter.call(inp, answer);
                                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                                            break;
                                        }
                                    }
                                }""", answer)
                                await page.wait_for_timeout(300)
                                await page.keyboard.press("Enter")
                            
                            await page.wait_for_timeout(1500)
                            continue
                except Exception as e_chatbot:
                    if "closed" in str(e_chatbot).lower():
                        print(f"     ✅ Naukri Applied (page closed): {job['title']} @ {job['company']}")
                        return ApplicationResult(job=job, status="applied")
                    # Input check failed silently, continue to other sections

                # 2. Check for quick-reply option chips/pills in chatbot
                # NOTE: only match actual pill/chip elements, NOT radio-style options
                chips_loc = container.locator("[class*='pill'], [class*='chip'], [class*='quick-reply'], button[class*='chat']")
                chip_count = await chips_loc.count()
                
                valid_chips = []
                if chip_count > 0:
                    for i in range(chip_count):
                        chip = chips_loc.nth(i)
                        try:
                            if await chip.is_visible():
                                text = (await chip.inner_text() or "").strip()
                                # Ignore very long texts as they might be descriptions, not chips
                                if text and len(text) < 100:
                                    valid_chips.append({"locator": chip, "text": text})
                        except:
                            continue
                            
                if valid_chips:
                    clicked = False
                    for c in valid_chips:
                        text_lower = c["text"].lower()
                        # Map preferred chip answers
                        if text_lower in ["yes", "immediate", "1", "1 year", "1-3 years", "0-1 years", "mca", "b.tech", "btech", "agree", "accept"]:
                            print(f"     💊 Clicking preferred chip: {c['text']}")
                            await c["locator"].click(force=True)
                            await page.wait_for_timeout(1000)
                            # Click Save/submit to advance after chip selection
                            for btn_sel in ["div.send:not(.disabled)", "div.sendMsg"]:
                                try:
                                    btn = container.locator(btn_sel).first
                                    if await btn.is_visible(timeout=500):
                                        await btn.click(force=True)
                                        print(f"     ✅ Clicked save after chip")
                                        await page.wait_for_timeout(1500)
                                        break
                                except:
                                    continue
                            clicked = True
                            break
                    if not clicked:
                        first_chip = valid_chips[0]
                        print(f"     💊 Clicking first chip: {first_chip['text']}")
                        await first_chip["locator"].click()
                        await page.wait_for_timeout(1500)
                    continue

                # 3. Generic Textarea filling (for non-chatbot screening questions or cover letters)
                try:
                    textareas = await container.locator("textarea").all()
                    for ta in textareas:
                        if await ta.is_visible() and not await ta.input_value():
                            placeholder = (await ta.get_attribute("placeholder") or "").lower()
                            # Fill cover letter or pitch
                            pitch = (
                                f"Hi, I am {os.getenv('USER_FULL_NAME', 'a candidate')}, a Software Developer with experience in Python, "
                                "Django, React, and Full Stack development. I have built robust backend systems and AI integrations. "
                                "I am very interested in this role and confident I can deliver high-quality results. Please find my "
                                "profile and resume attached. Thank you!"
                            )
                            await ta.fill(pitch)
                            await page.wait_for_timeout(500)
                except:
                    pass

                # 4. Auto-fill Naukri side-panel questionnaire (CTC, Experience, Degree, Yes/No)
                try:
                    # Fill Date Inputs (DOB etc.) — HTML date picker
                    date_inputs = await container.locator("input[type='date']").all()
                    for dinp in date_inputs:
                        if await dinp.is_visible() and not await dinp.input_value():
                            await dinp.fill("2002-04-08")

                    # Fill separate DD/MM/YYYY fields (Naukri splits DOB into 3 inputs)
                    # DOB: 08/04/2002
                    all_inputs = await container.locator("input").all()
                    for inp in all_inputs:
                        if await inp.is_visible() and not await inp.input_value():
                            ph = (await inp.get_attribute("placeholder") or "").strip().lower()
                            id_val = (await inp.get_attribute("id") or "").lower()
                            name_val = (await inp.get_attribute("name") or "").lower()
                            aria = (await inp.get_attribute("aria-label") or "").lower()
                            combined = ph + id_val + name_val + aria

                            if ph == "dd" or "day" in combined:
                                await inp.fill("08")
                                print("     📅 Filled DOB day: 08")
                            elif ph == "mm" or ("month" in combined and "year" not in combined):
                                await inp.fill("04")
                                print("     📅 Filled DOB month: 04")
                            elif ph == "yyyy" or ph == "yy" or ("year" in combined and "exp" not in combined and "birth" in combined):
                                await inp.fill("2002")
                                print("     📅 Filled DOB year: 2002")

                    # Fill Text Inputs
                    text_inputs = await container.locator("input[type='text'], input[type='number']").all()
                    for inp in text_inputs:
                        if await inp.is_visible() and not await inp.input_value():
                            ph = (await inp.get_attribute("placeholder") or "").strip().lower()
                            id_val = (await inp.get_attribute("id") or "").lower()
                            name_val = (await inp.get_attribute("name") or "").lower()
                            combined = ph + id_val + name_val
                            
                            # Skip DD/MM/YYYY fields already handled above
                            if ph in ["dd", "mm", "yyyy", "yy"]:
                                continue

                            if "dob" in combined or "date of birth" in combined or "birth" in combined or "birthday" in combined:
                                await inp.fill("08/04/2002")
                            elif "age" in combined:
                                await inp.fill("24")
                            elif "ctc" in combined or "salary" in combined or "income" in combined or "compensation" in combined:
                                await inp.fill("0")
                            elif "exp" in combined or "year" in combined:
                                await inp.fill("1")
                            elif "degree" in combined or "education" in combined or "qualification" in combined:
                                await inp.fill("MCA")
                            else:
                                await inp.fill("Yes")
                                
                    # Select Dropdowns
                    selects = await container.locator("select").all()
                    for sel in selects:
                        if await sel.is_visible():
                            opts = await sel.locator("option").all()
                            if len(opts) > 1:
                                val = await opts[1].get_attribute("value")
                                await sel.select_option(val)
                                
                    # Click Radio buttons, Checkboxes, and custom choice options in the drawer
                    try:
                        # Extract the current question from the drawer for context
                        drawer_question = await self._get_drawer_question(container)
                        if drawer_question:
                            print(f"     ❓ Drawer question: '{drawer_question}'")

                        options = []
                        for sel in ["label", "[role='radio']", "[role='checkbox']", "[role='option']", "[class*='pill']", "[class*='chip']", "[class*='option']", "[class*='radio']", "[class*='choice']"]:
                            try:
                                els = await container.locator(sel).all()
                                for el in els:
                                    if await el.is_visible():
                                        txt = (await el.inner_text() or "").strip()
                                        # Filter: skip containers with newlines (multi-option wrappers)
                                        if txt and len(txt) < 80 and "\n" not in txt:
                                            # Avoid duplicates and container/heading text
                                            if not any(o["text"] == txt for o in options):
                                                options.append({"text": txt, "locator": el})
                            except:
                                continue
                        
                        if options:
                            print(f"     📊 Found {len(options)} options in drawer: {[o['text'] for o in options]}")
                            # Use context-aware resolver to pick the right option
                            best = self._resolve_option_for_question(drawer_question, options)
                            if best:
                                print(f"     👉 Selecting option: '{best['text']}'")
                                await best["locator"].click(force=True)
                                await page.wait_for_timeout(1000)
                            else:
                                print(f"     🧠 Playwright unsure. Asking DOM LLM...")
                                instruction = f"Read the question '{drawer_question}' on screen. The user has the following skills: {self.RESUME_SKILLS}. Find the best matching option and click its radio button/checkbox. If no matching option exists, return 'skip'."
                                try:
                                    from shared_dom_llm import solve_with_dom_async
                                    await solve_with_dom_async(page, instruction)
                                    await page.wait_for_timeout(1500)
                                except Exception as fe:
                                    print(f"     ⚠️  DOM LLM fallback failed: {fe}")
                    except Exception as eo:
                        print(f"     ⚠️ Error in options handler: {eo}")
                except:
                    pass

                # 5. Click Submit / Apply / Save / Continue in modal/drawer
                clicked_btn = False
                
                # Primary: click the Naukri-specific div.send button (becomes enabled after option selected)
                # Use force=True to bypass sendMsgbtn_container intercepting pointer events
                for btn_sel in [
                    "div.send:not(.disabled)",
                    "div.sendMsg",
                    "button:has-text('Save')",
                    "button:has-text('Submit')",
                    "button:has-text('Continue')",
                    "button:has-text('Apply')",
                    "button[type='submit']",
                ]:
                    try:
                        btn = container.locator(btn_sel).first
                        if await btn.is_visible(timeout=500):
                            await btn.click(force=True)
                            print(f"     ✅ Clicked submit/save button in drawer: {btn_sel}")
                            await page.wait_for_timeout(2500)
                            clicked_btn = True
                            break
                    except:
                        continue
                
                # Fallback: JS click targeting the innermost matching element
                if not clicked_btn:
                    try:
                        js_clicked = await container.evaluate("""(containerEl) => {
                            // Collect ALL matching elements, then reverse to try innermost first
                            const buttons = Array.from(containerEl.querySelectorAll(
                                "button, [role='button'], a, div.send, div.sendMsg, span, input[type='button'], input[type='submit']"
                            )).reverse();
                            for (const el of buttons) {
                                const text = (el.innerText || "").trim().toLowerCase();
                                const cls = (el.className || "").toLowerCase();
                                // Skip disabled elements
                                if (cls.includes("disabled")) continue;
                                if (text === "save" || text === "submit" || text === "continue" || text === "apply" || 
                                    text === "save & continue" || text === "submit application" || text === "save details") {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 0 && rect.height > 0) {
                                        el.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }""")
                        if js_clicked:
                            print("     ✅ Clicked submit/save button in drawer (JS)")
                            await page.wait_for_timeout(2500)
                            clicked_btn = True
                    except Exception as ejs:
                        print(f"     ⚠️ JS button click failed: {ejs}")
                        
                # If no button was clicked, check if we're done
                if not clicked_btn and step >= 8:
                    if await self._is_applied(page):
                        print(f"     ✅ Naukri Applied: {job['title']} @ {job['company']}")
                        return ApplicationResult(job=job, status="applied")

                # After clicking Save, check if the drawer disappeared — that means form was submitted
                if clicked_btn:
                    drawer_gone = True
                    for sel in [".chatbot_Drawer", "[class*='chatbot_Drawer']", "[class*='Drawer']"]:
                        try:
                            if await page.locator(sel).first.is_visible(timeout=500):
                                drawer_gone = False
                                break
                        except:
                            pass
                    if drawer_gone:
                        await page.wait_for_timeout(1000)
                        if await self._is_applied(page):
                            print(f"     ✅ Naukri Applied: {job['title']} @ {job['company']}")
                            return ApplicationResult(job=job, status="applied")
                        # Drawer gone but no explicit success message — likely applied
                        print(f"     ✅ Naukri Applied (drawer closed): {job['title']} @ {job['company']}")
                        return ApplicationResult(job=job, status="applied")

            if await self._is_applied(page):
                print(f"     ✅ Naukri Applied: {job['title']} @ {job['company']}")
                return ApplicationResult(job=job, status="applied")

            return ApplicationResult(job=job, status="manual", reason="Could not complete form")

        except Exception as e:
            # If page/browser closed during apply, likely means application went through
            if "closed" in str(e).lower():
                print(f"     ✅ Naukri Applied (session ended): {job['title']} @ {job['company']}")
                return ApplicationResult(job=job, status="applied")
            return ApplicationResult(job=job, status="error", reason=str(e))

    async def _is_applied(self, page: Page) -> bool:
        for sel in [
            ":has-text('successfully applied')",
            ":has-text('Application submitted')",
            ":has-text('applied successfully')",
            ":has-text('application has been submitted')",
            ":has-text('Thank you for applying')",
            ":has-text('Thank you for your responses')",
            ":has-text('thank you for your interest')",
            ":has-text('already applied')",
            ":has-text('You have already')",
            ".success-message",
            "[class*='successMsg']",
            "[class*='appliedMsg']",
            "[class*='thankYou']",
            "[class*='applied-message']",
        ]:
            try:
                if await page.locator(sel).first.is_visible(timeout=600):
                    return True
            except:
                pass
        return False
