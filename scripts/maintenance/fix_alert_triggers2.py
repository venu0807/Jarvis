import os
import re

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../automations/alert_triggers.py'), 'r') as f:
    content = f.read()

# This script fixes the broken f-string concatenation in pg_isready block using regex
# Match the pattern: message=f"..." followed by multiple f"..." lines ending with a comma
pattern = r'''(message=)f"JARVIS cannot connect to PostgreSQL database\.\n\n"
                            f"Error: \{result\.stderr\.strip\(\)\}\n"
                            f"Time: \{datetime\.now\(\)\.strftime\('%Y-%m-%d %H:%M:%S'\)\}\n\n"
                            f"Impact:\n"
                            f"- Job tracking will fail\n"
                            f"- Event bus may not work\n"
                            f"- Metrics collection disrupted\n"
                            f"- All automations relying on DB will fail\n\n"
                            f"Immediate actions:\n"
                            f"1\. Check PostgreSQL service: sudo systemctl status postgresql\n"
                            f"2\. Restart if needed: sudo systemctl restart postgresql\n"
                            '3\. Verify connection: PGPASSWORD=jarvis psql -h localhost -U jarvis -d jarvis -c "SELECT 1;"\{NL\}'
                            f"4\. Check credentials in ~/\.jarvis/\.secrets/",'''

replacement = r'''\1(
                            "JARVIS cannot connect to PostgreSQL database.{NL}{NL}"
                            f"Error: {result.stderr.strip()}{NL}"
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                            "Impact:{NL}"
                            "- Job tracking will fail{NL}"
                            "- Event bus may not work{NL}"
                            "- Metrics collection disrupted{NL}"
                            "- All automations relying on DB will fail{NL}{NL}"
                            "Immediate actions:{NL}"
                            "1. Check PostgreSQL service: sudo systemctl status postgresql{NL}"
                            "2. Restart if needed: sudo systemctl restart postgresql{NL}"
                            '3. Verify connection: PGPASSWORD=jarvis psql -h localhost -U jarvis -d jarvis -c "SELECT 1;"{NL}'
                            "4. Check credentials in ~/.jarvis/.secrets/"
                        ),'''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../automations/alert_triggers.py'), 'w') as f:
    f.write(content)

print('Fixed pg_isready block via regex')