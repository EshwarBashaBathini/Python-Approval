from flask import Flask, render_template_string, jsonify
import threading
import time
import json
import os

app = Flask(__name__)
status_file = "approval_status.json"

# === Load or initialize status ===
def load_status():
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            return json.load(f)
    return {"status": "pending"}

def save_status(new_status):
    with open(status_file, "w") as f:
        json.dump({"status": new_status}, f)

@app.route('/')
def index():
    return "Approval server is running."

@app.route('/approve')
def approve():
    save_status("approved")
    threading.Timer(5.0, lambda: save_status("pending")).start()  # reset after 5 sec
    return render_template_string("""
        <h2 style="color: green;">✅ Pipeline Approved</h2>
        <p>Status will reset to pending shortly.</p>
    """)

@app.route('/reject')
def reject():
    save_status("rejected")
    threading.Timer(5.0, lambda: save_status("pending")).start()  # reset after 5 sec
    return render_template_string("""
        <h2 style="color: red;">❌ Pipeline Rejected</h2>
        <p>Status will reset to pending shortly.</p>
    """)

@app.route('/status')
def status():
    current = load_status()
    return jsonify(current)

@app.route('/reset', methods=['POST'])
def reset():
    save_status("pending")
    return "Status manually reset.", 200

if __name__ == "__main__":
    save_status("pending")  # Ensure initial state
    app.run(host="0.0.0.0", port=5000)
