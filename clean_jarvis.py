import os
import shutil

files_to_delete = [
    "com_out.txt", "commit_out.txt", "ps_out.txt", "tasks_out.txt",
    "commit.log", "tasks.txt", "schtasks.csv",
    "temp.ps1", "get_tasks.ps1", "elevate.vbs", "indeed_debug.png",
    "discover_workday_urls.py",
    "install_jarvis_tasks.bat", "fix_scheduled_tasks.bat",
    "automations/test_captcha.html", "automations/test_form.html",
    "automations/test_dom_llm.py", "automations/test_vision.py",
    "automations/test_hybrid_vision.py",
    "automations/linkedin-outreach/install_linkedin_task.ps1",
    "automations/linkedin-outreach/send_cold_mail.py",
    "automations/linkedin-outreach/linkedin_page_source.html",
    "automations/job-automation/indeed_debug.png",
    "automations/job-automation/naukri_headless_error.png",
    "automations/job-automation/install_job_automation_task.ps1",
    "automations/pinterest/debug_page.html",
    "automations/pinterest/debug_pin_builder.png",
    "automations/pinterest/failed_publish.png",
    "automations/pinterest/search_test.png",
    "automations/pinterest/search_test2.png",
    "automations/pinterest/fix.py", "automations/pinterest/fix_gen.py",
    "automations/pinterest/fix_poster.py", "automations/pinterest/test_gen.py",
    "automations/pinterest/test_trends.py", "automations/pinterest/test_trends_pw.py",
    "automations/pinterest/test_trends_pw2.py", "automations/pinterest/test_trends_url.py",
    "automations/pinterest/add_boat.py", "automations/pinterest/get_boards.py",
    "automations/pinterest/get_img.py",
    "automations/pinterest/install_pinterest_task.ps1",
    "automations/pinterest/install_scheduler.bat",
    "automations/pinterest/schedule_setup.py",
    "automations/pinterest/scheduled_runner.py",
    "automations/pinterest/run_daily.bat",
    "automations/pinterest/setup_scheduler.bat",
    "automations/pinterest/uninstall_scheduler.bat"
]

dirs_to_delete = [
    "automations/openclaw-archive",
    "automations/interview_scheduler_prep_bot"
]

base_dir = r"D:\Proposals\Jarvis"

for f in files_to_delete:
    path = os.path.join(base_dir, f)
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"Deleted file: {f}")
        except Exception as e:
            print(f"Failed to delete {f}: {e}")

for d in dirs_to_delete:
    path = os.path.join(base_dir, d)
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"Deleted dir: {d}")
        except Exception as e:
            print(f"Failed to delete {d}: {e}")

print("Cleanup finished.")
