import os
import re

FILES_TO_REFACTOR = [
    "main.py",
    "amazon_scraper.py",
    "extension_trends.py",
    "seo_optimizer.py",
    "bio_page.py",
    "cross_post.py",
    "fix_images.py",
    "cleanup_csv.py",
    "add_niches.py",
    "backfill_template.py"
]

def refactor():
    for filename in FILES_TO_REFACTOR:
        filepath = f"/home/venu/Proposals/Jarvis/automations/pinterest/{filename}"
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original = content
        
        # Add import if pandas is used and we are replacing csv logic
        if 'pd.read_csv' in content or 'to_csv' in content:
            if 'from database import' not in content:
                # insert after import pandas as pd
                content = content.replace("import pandas as pd", "import pandas as pd\nfrom database import get_products_df, save_products_df")
                # fallback if pandas is imported differently
                if 'from database import' not in content:
                    content = "from database import get_products_df, save_products_df\n" + content

        # Replace reading logic
        content = re.sub(r'pd\.read_csv\([^)]*\)', 'get_products_df()', content)
        
        # Replace writing logic
        # df.to_csv(CSV_FILE, index=False) -> save_products_df(df)
        content = re.sub(r'([a-zA-Z0-9_]+)\.to_csv\([^)]*\)', r'save_products_df(\1)', content)
        
        # Replace os.path.exists(CSV_FILE) with just True since DB always exists
        content = content.replace('os.path.exists(CSV_FILE)', 'True')
        content = content.replace('not os.path.exists(CSV_FILE)', 'False')
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Refactored {filename}")

if __name__ == "__main__":
    refactor()
