import os
import sys
import argparse
from pathlib import Path

try:
    JARVIS_HOME = str(Path(__file__).resolve().parent.parent.parent)
    if JARVIS_HOME not in sys.path:
        sys.path.insert(0, JARVIS_HOME)
    from policy import call_llm   # type: ignore
except Exception as e:
    raise SystemExit(f"FATAL: auto-publisher cannot import ~/.jarvis/policy: {e!r}.")

DRAFTS_DIR = Path(__file__).parent / "drafts"

# Files we definitely want the LLM to read if they exist
IMPORTANT_FILES = {
    "readme.md", "main.py", "app.py", "index.js", 
    "requirements.txt", "package.json", "dockerfile",
    "scraper.py", "composer.py"
}

def scan_directory(project_path: Path):
    """Scans the directory and returns a tree structure and file contents."""
    tree = []
    file_contents = {}
    
    for root, dirs, files in os.walk(project_path):
        # Ignore common clutter
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules', 'venv', 'env', '.idea', '.vscode')]
        
        level = str(root).replace(str(project_path), '').count(os.sep)
        indent = ' ' * 4 * (level)
        tree.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            tree.append(f"{subindent}{f}")
            
            # Read important files to give context to the LLM
            if f.lower() in IMPORTANT_FILES or f.endswith(('.py', '.js', '.ts', '.md')) and level < 2:
                # Don't read too many files to avoid context overflow, just a few key ones
                if len(file_contents) < 5: 
                    file_path = os.path.join(root, f)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                            # Truncate large files
                            if len(content) > 3000:
                                content = content[:3000] + "\n...[TRUNCATED]"
                            file_contents[f] = content
                    except Exception:
                        pass
                        
    return "\n".join(tree), file_contents

def generate_blog_post(project_name: str, tree: str, contents: dict):
    print(f"🤖 Generating blog post for {project_name}...")
    
    content_str = ""
    for filename, text in contents.items():
        content_str += f"--- {filename} ---\n```\n{text}\n```\n\n"

    prompt = f"""You are a Senior Developer Advocate and Technical Writer. 
I just built a new side project called '{project_name}'.

Here is the directory structure of the project:
{tree}

Here is the source code of the most important files:
{content_str}

TASK:
Write a highly engaging, professional, and SEO-friendly technical blog post about this project for Dev.to or Medium.

FORMAT:
Use Markdown. Include the following sections:
1. A catchy title and a strong hook/introduction.
2. The Problem: Why I built this (deduce this from the code context).
3. The Architecture: How it works under the hood (mention the specific tech stack used).
4. Code Deep-Dive: Highlight the most interesting or clever part of the code (use markdown code blocks).
5. Conclusion & What's Next.

Make it read like it was written by a passionate software engineer. Do not include placeholders, just write the actual post.
"""

    try:
        # We can allow cloud here if it's a big project, but local is fine for side projects.
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="local",
            pii_acknowledged=False, # Just source code
            task_label="auto_publisher",
            timeout_s=300
        )
        return result.text
    except Exception as e:
        print(f"❌ LLM generation failed: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Auto-Publisher: Generate a blog post from a project directory.")
    parser.add_argument("project_path", help="Path to the project directory")
    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.exists() or not project_path.is_dir():
        print(f"❌ Error: {project_path} is not a valid directory.")
        return

    project_name = project_path.name
    print(f"📂 Scanning project: {project_name}")
    
    tree, file_contents = scan_directory(project_path)
    print(f"✅ Scanned {len(file_contents)} key files.")
    
    blog_post = generate_blog_post(project_name, tree, file_contents)
    
    if blog_post:
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        output_file = DRAFTS_DIR / f"{project_name}_blog_post.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(blog_post)
        print(f"🎉 Success! Blog post saved to {output_file}")

if __name__ == "__main__":
    main()
