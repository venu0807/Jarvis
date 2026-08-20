#!/usr/bin/env python3
"""Test each alert check individually"""
import sys
sys.path.insert(0, "/home/venu/Proposals/Jarvis")

from automations.alert_triggers import (
    check_job_apply_count,
    check_postgres_connection,
    check_scheduler_health,
    check_disk_space,
    check_ollama_availability,
    check_portal_sessions,
)
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("=== Job Apply Count ===")
result = check_job_apply_count()
print(f"Result: {result}")

print("\n=== PostgreSQL ===")
result = check_postgres_connection()
print(f"Result: {result}")

print("\n=== Scheduler Health ===")
result = check_scheduler_health()
print(f"Result: {result}")

print("\n=== Disk Space ===")
result = check_disk_space()
print(f"Result: {result}")

print("\n=== Ollama ===")
result = check_ollama_availability()
print(f"Result: {result}")

print("\n=== Portal Sessions ===")
result = check_portal_sessions()
print(f"Result: {result}")