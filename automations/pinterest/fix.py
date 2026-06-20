import re

with open('poster.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_code = '''
_GLOBAL_BROWSER_MGR = None
_GLOBAL_CONTEXT = None
_GLOBAL_PAGE = None

def cleanup_browser():
    global _GLOBAL_BROWSER_MGR, _GLOBAL_CONTEXT, _GLOBAL_PAGE
    if _GLOBAL_BROWSER_MGR or _GLOBAL_PAGE:
        print('\n  🧹 Cleaning up browser session...')
    try:
        from jarvis_browser import safe_close_sync
        if _GLOBAL_PAGE: safe_close_sync(_GLOBAL_PAGE)
        if _GLOBAL_CONTEXT: safe_close_sync(_GLOBAL_CONTEXT)
        if _GLOBAL_BROWSER_MGR:
            try: _GLOBAL_BROWSER_MGR.__exit__(None, None, None)
            except: pass
    except Exception as e:
        print(f'  ⚠️ Cleanup error: {e}')
    finally:
        _GLOBAL_PAGE = None
        _GLOBAL_CONTEXT = None
        _GLOBAL_BROWSER_MGR = None

'''

content = content.replace('def _post_via_browser(image_path: str, title: str, link: str, description: str, board_name: str = None) -> bool:', new_code + 'def _post_via_browser(image_path: str, title: str, link: str, description: str, board_name: str = None) -> bool:')

old_init = '''    try:
        with SyncBrowser(headless=False) as browser_mgr:
            context = browser_mgr.launch_persistent(
                BROWSER_USER_DATA_DIR,
                extra_kwargs={"viewport": {"width": 1280, "height": 800}},
            )
            page = context.new_page()'''

new_init = '''    try:
        global _GLOBAL_BROWSER_MGR, _GLOBAL_CONTEXT, _GLOBAL_PAGE
        if _GLOBAL_BROWSER_MGR is None:
            print(f'  📂 Initializing Global Browser Profile: {BROWSER_USER_DATA_DIR}')
            _GLOBAL_BROWSER_MGR = SyncBrowser(headless=False)
            _GLOBAL_BROWSER_MGR.__enter__()
            _GLOBAL_CONTEXT = _GLOBAL_BROWSER_MGR.launch_persistent(
                BROWSER_USER_DATA_DIR,
                extra_kwargs={"viewport": {"width": 1280, "height": 800}},
            )
            _GLOBAL_PAGE = _GLOBAL_CONTEXT.new_page()
            page = _GLOBAL_PAGE
        else:
            print('  🌐 Reusing open browser window...')
            page = _GLOBAL_PAGE'''

content = content.replace(old_init, new_init)

lines = content.split('\n')
in_block = False
for i, line in enumerate(lines):
    if 'page = _GLOBAL_PAGE' in line and 'Reusing open browser window' in lines[i-1]:
        in_block = True
        continue
    if in_block:
        if line.startswith('    except Exception as e:') and 'Browser posting error:' in lines[i+1]:
            in_block = False
        elif line.startswith('            '):
            lines[i] = line[4:]
        elif line == '        ':
            lines[i] = '    '

content = '\n'.join(lines)

with open('poster.py', 'w', encoding='utf-8') as f:
    f.write(content)
