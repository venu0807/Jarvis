import requests
import time
import speech_recognition as sr
import json
import os

# Backend URL in WSL
API_URL = "http://localhost:8005/api/transcript"

print("🎙️ Starting Native Windows Ghost Listener...")
print("==================================================")
print("This script captures your audio natively on Windows")
print("and streams it silently to the WSL AI backend.")
print("==================================================")

r = sr.Recognizer()

# Adjust for ambient noise
with sr.Microphone() as source:
    print("Calibrating background noise... please wait 2 seconds.")
    r.adjust_for_ambient_noise(source, duration=2)
    print("✅ Calibration complete! Listening for interview questions...\n")

def send_transcript(text: str, is_final: bool = True):
    try:
        requests.post(API_URL, json={"text": text, "is_final": is_final})
    except requests.exceptions.ConnectionError:
        print("⚠️  Warning: Cannot connect to WSL backend. Make sure server.py is running on port 8005.")

while True:
    with sr.Microphone() as source:
        try:
            # Listen in chunks
            audio = r.listen(source, timeout=10, phrase_time_limit=15)
            
            # Using Google Web Speech API for instant latency (no CUDA required on Windows)
            # You can easily swap this to r.recognize_whisper() if you install openai-whisper locally
            text = r.recognize_google(audio)
            
            if text:
                print(f"[Captured]: {text}")
                send_transcript(text, is_final=True)
                
        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
        except Exception as e:
            print(f"Error: {e}")
