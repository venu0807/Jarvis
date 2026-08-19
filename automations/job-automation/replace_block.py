with open("/home/venu/Proposals/Jarvis/automations/job-automation/auto_applier.py", "r") as f:
    content = f.read()

old_block = """    async with AsyncBrowser(headless=is_headless) as browser_mgr:
        for name, cls in portal_map.items():
            session_file = SESSION_DIR / f"{name}.json"
            if session_file.exists():
                print(f"\n💾 {name}: loading saved session from {session_file.name}")
            context = await browser_mgr.new_context_with_session(session_file)

            try:
                results, session_ok = await run_portal(name, cls, context)
                all_results.extend(results)
                if not session_ok:
                    needs_relogin.append(name)
                await browser_mgr.save_session(context, session_file)
            except Exception as e:
                print(f"\n❌ {name} portal crashed: {e}")
                traceback.print_exc()
            finally:
                await safe_close_async(context)

    # Save all scraped jobs to the SQLite Database (for Interview Prep Bot)"""

new_block = """    async def _run_single_portal(name: str, cls, browser_mgr: AsyncBrowser) -> tuple[str, list, bool]:
        \"\"\"Run one portal and return (name, results, session_ok).\"\"\"
        session_file = SESSION_DIR / f"{name}.json"
        if session_file.exists():
            print(f"\n💾 {name}: loading saved session from {session_file.name}")
        context = await browser_mgr.new_context_with_session(session_file)
        try:
            results, session_ok = await run_portal(name, cls, context)
            await browser_mgr.save_session(context, session_file)
            return name, results, session_ok
        except Exception as e:
            print(f"\n❌ {name} portal crashed: {e}")
            traceback.print_exc()
            return name, [], False
        finally:
            await safe_close_async(context)

    async with AsyncBrowser(headless=is_headless) as browser_mgr:
        # Run all portals in parallel using asyncio.gather
        tasks = [
            _run_single_portal(name, cls, browser_mgr)
            for name, cls in portal_map.items()
        ]
        portal_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in portal_results:
            if isinstance(result, Exception):
                print(f"\n❌ Portal task raised: {result}")
                continue
            name, results, session_ok = result
            all_results.extend(results)
            if not session_ok:
                needs_relogin.append(name)

    # Save all scraped jobs to the SQLite Database (for Interview Prep Bot)"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open("/home/venu/Proposals/Jarvis/automations/job-automation/auto_applier.py", "w") as f:
        f.write(content)
    print("SUCCESS: Replaced successfully")
else:
    print("FAILED: old_block not found")