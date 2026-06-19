import re
with open('poster.py', 'r', encoding='utf-8') as f: content = f.read()

new_logic = '''                    if board_dropdown.is_visible():
                        print(f"  📌 Selecting board: {target_board}")
                        board_dropdown.click()
                        time.sleep(2)
                        
                        # 1. ALWAYS search first
                        search_input = page.locator('input[placeholder*="Search"]').first
                        if search_input.is_visible():
                            search_input.fill(target_board)
                            time.sleep(2)
                            
                        # 2. Check if the board option appeared
                        try:
                            board_option = page.locator(f'[data-test-id="board-card-{target_board}"], [data-test-id="board-card"]:has-text("{target_board}")').first
                            if board_option.is_visible(timeout=3000):
                                board_option.click()
                            else:
                                raise Exception("Not found")
                        except Exception:
                            # 3. If still not found, create it
                            print(f"  ⚠️  Board '{target_board}' not found. Attempting to create it...")
                            try:
                                create_btn = page.locator('div[role="button"]:has-text("Create board")').first
                                if create_btn.is_visible():
                                    create_btn.click()
                                    time.sleep(1)
                                    name_input = page.locator('input[id="boardEditName"]').first
                                    if name_input.is_visible():
                                        name_input.fill(target_board)
                                    submit_btn = page.locator('button:has-text("Create")').last
                                    submit_btn.click()
                                    time.sleep(3)
                                    print(f"  ✅ Created new board: {target_board}")
                                else:
                                    page.locator('[data-test-id="board-card"]').first.click(timeout=5000)
                            except Exception as e:
                                print(f"  ⚠️  Failed to create board: {e}")
                                page.locator('[data-test-id="board-card"]').first.click(timeout=5000)'''

old_logic_pattern = r'                    if board_dropdown\.is_visible\(\):\n                        print\(f"  📌 Selecting board: \{target_board\}"\)\n                        board_dropdown\.click\(\)\n                        time\.sleep\(2\)\n                        try:\n                            board_option = page\.locator\(f\'\[data-test-id="board-card-\{target_board\}"\], \[data-test-id="board-card"\]:has-text\("\{target_board\}"\)\'\)\.first\n                            if board_option\.is_visible\(\):\n                                board_option\.click\(timeout=3000\)\n                            else:\n                                raise Exception\("Not found"\)\n                        except Exception:\n                            print\(f"  ⚠️  Board \'\{target_board\}\' not found\. Attempting to create it\.\.\."\)\n                            try:\n                                # Pinterest search input inside dropdown\n                                search_input = page\.locator\(\'input\[placeholder\*="Search"\]\'\)\.first\n                                if search_input\.is_visible\(\):\n                                    search_input\.fill\(target_board\)\n                                    time\.sleep\(2\)\n                                create_btn = page\.locator\(\'div\[role="button"\]:has-text\("Create board"\)\'\)\.first\n                                if create_btn\.is_visible\(\):\n                                    create_btn\.click\(\)\n                                    time\.sleep\(1\)\n                                    name_input = page\.locator\(\'input\[id="boardEditName"\]\'\)\.first\n                                    if name_input\.is_visible\(\):\n                                        name_input\.fill\(target_board\)\n                                    submit_btn = page\.locator\(\'button:has-text\("Create"\)\'\)\.last\n                                    submit_btn\.click\(\)\n                                    time\.sleep\(3\)\n                                    print\(f"  ✅ Created new board: \{target_board\}"\)\n                                else:\n                                    page\.locator\(\'\[data-test-id="board-card"\]\'\)\.first\.click\(timeout=5000\)\n                            except Exception as e:\n                                print\(f"  ⚠️  Failed to create board: \{e\}"\)\n                                page\.locator\(\'\[data-test-id="board-card"\]\'\)\.first\.click\(timeout=5000\)'

content = re.sub(old_logic_pattern, new_logic, content, flags=re.DOTALL)
with open('poster.py', 'w', encoding='utf-8') as f: f.write(content)
print('DONE')
