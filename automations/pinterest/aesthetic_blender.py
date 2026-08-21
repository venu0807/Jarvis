import os
import sys
import tempfile
import subprocess

BACKGROUNDS = {
    "tech": ("bg_aesthetic_workspace.png", "Cozy Workspace", "Amazon Finds"),
    "study_supplies": ("bg_aesthetic_workspace.png", "Study Setup", "Must Haves"),
    "dorm_decor": ("bg_moody_ambient.png", "Dorm Decor", "Cozy Finds"),
    "cozy_home": ("bg_moody_ambient.png", "Cozy Home", "Top Picks"),
    "self_care": ("bg_minimalist.png", "Self Care", "Essentials"),
    "kitchen": ("bg_minimalist.png", "Kitchen", "Gadgets"),
    "wellness": ("bg_minimalist.png", "Wellness", "Favorites"),
    "fashion": ("bg_moody_ambient.png", "Aesthetic Fits", "Must Haves"),
    "tech_gadgets": ("bg_aesthetic_workspace.png", "Tech Gadgets", "Amazon Finds"),
    "mens_fashion": ("bg_aesthetic_workspace.png", "Mens Style", "Essentials"),
    "womens_fashion": ("bg_moody_ambient.png", "Womens Style", "Essentials"),
    "default": ("bg_moody_ambient.png", "Aesthetic Finds", "Top Picks")
}

def _run_playwright_standalone(temp_path: str, output_path: str):
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1008, "height": 1504})
            # Use file:// URL with proper path escaping for Windows
            file_url = f"file:///{temp_path.replace(os.sep, '/')}"
            page.goto(file_url)
            page.wait_for_timeout(2000)
            page.screenshot(path=output_path, type="jpeg", quality=95)
            browser.close()
    except Exception as e:
        print(f"  ❌ Playwright rendering process failed: {e}")

def generate_aesthetic_pin(image_url: str, category: str, output_path: str, title: str = "", subtitle: str = "", price: str = "", product_image_url: str = ""):
    """
    Generates an aesthetic Pinterest pin using HTML/CSS and Playwright.
    """
    print(f"🎨 Generating aesthetic HTML-based pin for {category} product...")

    base_dir = os.path.dirname(__file__)

    # The lifestyle image is now the full-bleed background
    if not image_url.startswith("http"):
        lifestyle_image_url = f"file:///{os.path.abspath(image_url).replace(os.sep, '/')}"
    else:
        lifestyle_image_url = image_url

    import random
    templates = ["pin_template.html", "pin_template_2.html", "pin_template_3.html", "pin_template_v4.html", "pin_template_v5.html", "pin_template_v6.html", "pin_template_v7.html", "pin_template_v8.html"]
    selected_template = random.choice(templates)
    template_path = os.path.join(base_dir, "templates", selected_template)
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Truncate title if it's too long to fit nicely
    short_title = str(title)[:60] + "..." if len(str(title)) > 60 else str(title)

    # Ensure all replacement values are strings
    html_content = html_content.replace("{lifestyle_image_url}", str(lifestyle_image_url))
    html_content = html_content.replace("{product_image_url}", str(product_image_url if product_image_url else lifestyle_image_url))
    html_content = html_content.replace("{title}", str(short_title))
    html_content = html_content.replace("{subtitle}", str(subtitle))
    html_content = html_content.replace("{price}", str(price))

    fd, temp_path = tempfile.mkstemp(suffix=".html")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Avoid multiprocessing fork deadlocks by using subprocess to spawn a fresh python interpreter
        # Properly escape paths for Windows in the subprocess command - use forward slashes and raw strings
        safe_temp = temp_path.replace('\\', '\\\\')
        safe_output = output_path.replace('\\', '\\\\')
        # Use regular strings with proper escaping for subprocess
        script = f"from aesthetic_blender import _run_playwright_standalone; _run_playwright_standalone('{safe_temp}', '{safe_output}')"
        # Ensure PYTHONPATH includes the current directory so the module can be imported
        env = os.environ.copy()
        env['PYTHONPATH'] = base_dir + os.pathsep + env.get('PYTHONPATH', '')
        result = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True, env=env, cwd=base_dir)

        if os.path.exists(output_path):
            print(f"  ✅ Saved aesthetic pin to {output_path}")
            return True
        else:
            print(f"  ❌ Output file not created: {output_path}")
            print(f"  subprocess stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Failed to spawn Playwright process: {e}")
        return False
    finally:
        try:
            os.close(fd)
        except:
            pass
        try:
            os.remove(temp_path)
        except:
            pass

if __name__ == "__main__":
    pass