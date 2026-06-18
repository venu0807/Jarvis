@echo off
cd /d "D:\Proposals\Jarvis\automations\interview_scheduler_prep_bot"
call conda activate interview_bot
python email_listener.py >> cron.log 2>&1
