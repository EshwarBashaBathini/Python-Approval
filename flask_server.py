from flask import Flask, request, jsonify, render_template_string
import uuid
import time
import threading 

app = Flask(__name__)
#update the flask code

status_store = {}
store_lock = threading.Lock()

TOKEN_TTL_SECONDS = 24 * 3600  # 24 hours expiration


def is_token_expired(created_time):
    return (time.time() - created_time) > TOKEN_TTL_SECONDS


@app.route('/generate_token', methods=['POST'])
def generate_token():
    token = str(uuid.uuid4())
    with store_lock:
        status_store[token] = {
            "status": "pending",
            "reason": "",
            "used": False,
            "created": time.time()
        }
    return jsonify({"token": token})


@app.route('/approval/<token>', methods=['GET'])
def approval_page(token):
    with store_lock:
        data = status_store.get(token)

    if not data:
        return "Invalid or expired token", 404

    if is_token_expired(data['created']):
        # Soft orange/yellow background for expired link
        return """
        <div style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 30px; text-align: center; background: #fff3cd; border-radius: 10px; color: #856404;">
            <h2>Expired Link</h2>
            <p>This approval link has expired.</p>
        </div>
        """, 410

    if data["used"]:
        return """
        <div style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 30px; text-align: center; background: #f8d7da; border-radius: 10px; color: #842029;">
            <h2>Link Expired</h2>
            <p>This approval link has already been used and is no longer valid.</p>
        </div>
        """, 410

    # Approval form page
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Approval Request</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f5f5f5;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            .approval-container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 500px;
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
            }
            select, textarea {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: inherit;
                font-size: 16px;
            }
            textarea {
                min-height: 100px;
                resize: vertical;
            }
            .radio-group {
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
            }
            .radio-option {
                display: flex;
                align-items: center;
            }
            .radio-option input {
                margin-right: 8px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;
                transition: background-color 0.3s;
            }
            button:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="approval-container">
            <h1>Approval Request</h1>
            <form method="POST" action="/submit_decision/{{ token }}">
                <div class="form-group">
                    <label>Decision:</label>
                    <div class="radio-group">
                        <div class="radio-option">
                            <input type="radio" id="approved" name="decision" value="approved" required>
                            <label for="approved">Approve</label>
                        </div>
                        <div class="radio-option">
                            <input type="radio" id="rejected" name="decision" value="rejected">
                            <label for="rejected">Reject</label>
                        </div>
                    </div>
                </div>
                <div class="form-group">
                    <label for="reason">Reason:</label>
                    <textarea id="reason" name="reason" required></textarea>
                </div>
                <button type="submit">Submit Decision</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, token=token)


@app.route('/submit_decision/<token>', methods=['POST'])
def submit_decision(token):
    with store_lock:
        data = status_store.get(token)

    if not data:
        return """
        <div style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 30px; text-align: center; background: #f8d7da; border-radius: 10px; color: #842029;">
            <h2>Invalid Link</h2>
            <p>This approval link is invalid or expired.</p>
        </div>
        """, 404

    if is_token_expired(data['created']):
        return """
        <div style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 30px; text-align: center; background: #fff3cd; border-radius: 10px; color: #856404;">
            <h2>Expired Link</h2>
            <p>This approval link has expired and cannot be used.</p>
        </div>
        """, 410

    if data["used"]:
        return """
        <div style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 30px; text-align: center; background: #f8d7da; border-radius: 10px; color: #842029;">
            <h2>Link Expired</h2>
            <p>This approval link has already been used and cannot be reused.</p>
        </div>
        """, 410

    decision = request.form.get('decision')
    reason = request.form.get('reason', '').strip()

    if decision not in ['approved', 'rejected'] or not reason:
        return """
        <div style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 30px; text-align: center; background: #fff3cd; border-radius: 10px; color: #856404;">
            <h2>Missing Information</h2>
            <p>Both decision and reason are required to proceed.</p>
        </div>
        """, 400

    with store_lock:
        data['status'] = decision
        data['reason'] = reason
        data['used'] = True
        data['decision_time'] = time.strftime('%Y-%m-%d %H:%M:%S')

    # Thank you page with conditional styling for rejected (red) or approved (green)
    if decision == "rejected":
        bg_color = "#f8d7da"
        text_color = "#842029"
        box_shadow = "0 6px 20px rgba(220,53,69,.3)"
    else:
        bg_color = "#e9f7ef"
        text_color = "#155724"
        box_shadow = "0 6px 20px rgba(40,167,69,.3)"

    thank_you_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Thank You</title>
      <style>
        body {{
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          max-width: 600px;
          margin: 50px auto;
          background: {bg_color};
          padding: 40px 50px;
          border-radius: 12px;
          box-shadow: {box_shadow};
          color: {text_color};
          text-align: center;
        }}
        h2 {{
          font-size: 28px;
          margin-bottom: 20px;
        }}
        p {{
          font-size: 18px;
          line-height: 1.6;
        }}
      </style>
    </head>
    <body>
      <h2>Thank You for Your Response!</h2>
      <p>Your decision has been recorded as: <strong>{decision.capitalize()}</strong></p>
      <p>Submitted at: <strong>{data['decision_time']}</strong></p>
      <p>Reason Provided: <em>{reason}</em></p>
    </body>
    </html>
    """
    return render_template_string(thank_you_template)


@app.route('/status/<token>', methods=['GET'])
def check_status(token):
    with store_lock:
        data = status_store.get(token)

    if not data:
        return jsonify({"error": "Invalid token"}), 404

    if is_token_expired(data["created"]):
        return jsonify({"error": "Token expired"}), 410

    return jsonify({
        "status": data["status"],
        "reason": data["reason"],
        "used": data["used"],
        "decision_time": data.get("decision_time", "")
    })


if __name__ == '__main__':
    app.run(debug=True)