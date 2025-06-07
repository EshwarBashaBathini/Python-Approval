from flask import Flask, request, render_template_string, jsonify
import os
import json
import uuid

app = Flask(__name__)
TOKENS_FILE = "tokens.json"

# === Token Persistence Utilities ===
def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

# === Helper to build styled response page ===
def build_response(title, message, color):
    # Style specific messages
    styled_message = message
    if "rejected" in message.lower():
        styled_message = f'<span style="color: #b02a37; font-weight: 600;">{message}</span>'
    elif "already been used" in message.lower():
        styled_message = f'<span style="color: #e07b00; font-style: italic;">{message}</span>'
    elif "thank you for approving" in message.lower():
        styled_message = f'<span style="color: #2d7a2d; font-weight: 600;">{message}</span>'

    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f9f9f9;
                text-align: center;
                padding: 80px 20px;
                color: #333;
            }}
            h2 {{
                color: {color};
                font-size: 26px;
                margin-bottom: 20px;
            }}
            p {{
                font-size: 17px;
                line-height: 1.6;
                max-width: 600px;
                margin: 0 auto 30px;
                color: #444;
            }}
            .button {{
                display: inline-block;
                padding: 8px 14px;
                font-size: 14px;
                font-weight: 600;
                border: none;
                border-radius: 6px;
                color: white;
                background-color: {color};
                text-decoration: none;
                cursor: pointer;
                transition: all 0.25s ease;
                box-shadow: 0 3px 6px rgba(0, 0, 0, 0.15);
                user-select: none;
            }}
            .button:hover {{
                background-color: #000000cc;
                text-decoration: underline;
                transform: scale(1.05);
            }}
        </style>
    </head>
    <body>
        <h2>{title}</h2>
        <p>{styled_message}</p>
        <a href="/" class="button">Go Home</a>
    </body>
    </html>
    """)

# === Routes ===
@app.route('/')
def index():
    return "✅ Token-based Approval Server is running."

@app.route('/generate_token', methods=['POST'])
def generate_token():
    tokens = load_tokens()
    token = str(uuid.uuid4())
    tokens[token] = {"status": "pending", "used": False}
    save_tokens(tokens)
    return jsonify({"token": token})

@app.route('/approve/<token>')
def approve(token):
    tokens = load_tokens()
    if token not in tokens:
        return "❌ Invalid token.", 404
    if tokens[token]["used"]:
        return build_response(
            "⚠️ Link Already Used",
            "This approval link has already been used. If you believe this is an error, please contact the CI/CD administrator.",
            "#ff9800"
        )

    tokens[token]["status"] = "approved"
    tokens[token]["used"] = True
    save_tokens(tokens)
    print(f"🔔 Approved token: {token}")
    return build_response(
        "✅ Pipeline Approved",
        "Thank you for approving. The pipeline will proceed to the next stage shortly.",
        "#28a745"
    )

@app.route('/reject/<token>')
def reject(token):
    tokens = load_tokens()
    if token not in tokens:
        return "❌ Invalid token.", 404
    if tokens[token]["used"]:
        return build_response(
            "⚠️ Link Already Used",
            "This rejection link has already been used. If you believe this is an error, please contact the CI/CD administrator.",
            "#ff9800"
        )

    tokens[token]["status"] = "rejected"
    tokens[token]["used"] = True
    save_tokens(tokens)
    print(f"❌ Rejected token: {token}")
    return build_response(
        "❌ Pipeline Rejected",
        "You have rejected the pipeline. The deployment has been stopped as requested.",
        "#b02a37"
    )

@app.route('/status/<token>')
def status(token):
    tokens = load_tokens()
    if token not in tokens:
        return jsonify({"error": "Invalid token"}), 404
    return jsonify({"status": tokens[token]["status"]})

# === Run App ===
if __name__ == "__main__":
    # Initialize the file if it doesn't exist
    if not os.path.exists(TOKENS_FILE):
        save_tokens({})
    app.run(host="0.0.0.0", port=5000)
