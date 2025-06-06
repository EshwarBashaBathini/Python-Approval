import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import time
import threading
from flask import Flask, render_template_string, redirect

# === CONFIGURATION ===
smtp_user = "yaswanthkumarch2001@gmail.com"
smtp_password = "uqjc bszf djfw bsor"  # Use Gmail App Password
to_email = "eshwar@middlewaretalents.com"
public_url = "https://0287-136-232-205-158.ngrok-free.app"  # Replace with actual ngrok HTTPS URL

# Flask app for approval server
app = Flask(__name__)
approval_status = "pending"

@app.route('/')
def index():
    return redirect('/status')

@app.route('/approve')
def approve():
    global approval_status
    approval_status = "approved"
    return render_template_string("""
    <h2 style="color: green;">✅ Pipeline Approved</h2>
    <p>Thank you for your response.</p>
    """)

@app.route('/reject')
def reject():
    global approval_status
    approval_status = "rejected"
    return render_template_string("""
    <h2 style="color: red;">❌ Pipeline Rejected</h2>
    <p>Thank you for your response.</p>
    """)

@app.route('/status')
def status():
    return approval_status, 200

# Start Flask server in background thread
def start_server():
    app.run(port=5000)

server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

# Allow Flask server to initialize
time.sleep(2)

# === Email Composition ===
status_url = f"{public_url}/status"
approve_url = f"{public_url}/approve"
reject_url = f"{public_url}/reject"

subject = "Harness Pipeline Approval Needed"
html_body = f"""
<html>
  <body style="font-family: Arial;">
    <p>Hi,<br><br>
       Please review and take action on the pipeline.<br><br>
       <a href="{approve_url}" style="padding: 10px 20px; background-color: green; color: white; text-decoration: none;">Approve</a>
       &nbsp;
       <a href="{reject_url}" style="padding: 10px 20px; background-color: red; color: white; text-decoration: none;">Reject</a><br><br>
       Thanks,<br>CI Bot
    </p>
  </body>
</html>
"""

msg = MIMEMultipart('alternative')
msg['From'] = smtp_user
msg['To'] = to_email
msg['Subject'] = subject
msg.attach(MIMEText(html_body, 'html'))

# Send Email
try:
    print("📧 Sending email...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(smtp_user, smtp_password)
    server.sendmail(smtp_user, to_email, msg.as_string())
    server.quit()
    print("✅ Email sent.")
except Exception as e:
    print("❌ Failed to send email:", e)
    exit(1)

# Poll for approval
print("⏳ Waiting for approval (10 minutes max)...")
for i in range(60):
    try:
        res = requests.get(status_url)
        res.raise_for_status()
        status = res.text.strip().lower()
        if status in ["approved", "rejected"]:
            print(f"🔔 Pipeline {status.upper()}.")
            break
    except Exception as err:
        print(f"🔁 Check {i+1}/60 failed:", err)
    time.sleep(10)
else:
    print("⌛ Approval timeout.")

# === Keep the server alive ===
print("🚀 Flask approval server is still running at:", public_url)
print("✅ You can revisit /approve, /reject, or /status anytime.")


