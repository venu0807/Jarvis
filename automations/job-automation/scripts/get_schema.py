import sqlite3

conn = sqlite3.connect('/home/venu/Proposals/Jarvis/automations/job-automation/output/jobs.db')
cursor = conn.cursor()
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
for row in cursor.fetchall():
    print(row[0])
