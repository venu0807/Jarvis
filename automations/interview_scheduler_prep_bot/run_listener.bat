@echo off
cd /d "C:\Users\Venu\.jarvis\automations\interview_scheduler_prep_bot"
call conda activate interview_bot
python email_listener.py
