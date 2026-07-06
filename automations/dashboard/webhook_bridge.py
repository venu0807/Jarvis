import http.server
import socketserver
import subprocess
import threading
import json
import os

PORT = 5000
PINTEREST_DIR = "/home/venu/Proposals/Jarvis/automations/pinterest"
LINKEDIN_DIR = "/home/venu/Proposals/Jarvis/automations/linkedin" # Assuming this exists or will exist

class WebhookHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        # Handle CORS preflight for browser requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        # Allow requests from the UI dashboard
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {"status": "success", "message": "Bot triggered"}

        if self.path == '/run/pinterest':
            print("🚀 TRIGGER RECEIVED: Starting Pinterest Bot...")
            # Run asynchronously so the UI button doesn't freeze waiting for the bot to finish
            # Uses the venv python to ensure dependencies load correctly
            cmd = ["venv/bin/python", "main.py", "--count", "20"]
            subprocess.Popen(cmd, cwd=PINTEREST_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            response["message"] = "Pinterest Bot started in the background"

        elif self.path == '/run/linkedin':
            print("🚀 TRIGGER RECEIVED: Starting LinkedIn Bot...")
            # Placeholder command - update this when LinkedIn bot is ready
            # cmd = ["venv/bin/python", "main.py"]
            # subprocess.Popen(cmd, cwd=LINKEDIN_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            response["message"] = "LinkedIn Bot started in the background"
            
        else:
            self.send_response(404)
            response = {"status": "error", "message": "Endpoint not found"}

        self.wfile.write(json.dumps(response).encode())

def start_server():
    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        print(f"✅ Webhook Bridge running at http://localhost:{PORT}")
        print("Waiting for signals from your Dashboard...")
        httpd.serve_forever()

if __name__ == "__main__":
    start_server()
