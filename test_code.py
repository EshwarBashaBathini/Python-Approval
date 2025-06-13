from flask import Flask, jsonify, request
import subprocess

app = Flask(__name__)

@app.route("/restart_uf", methods=["GET", "POST"])
def restart_uf():
    if request.method == "GET":
        return "Send a POST request to this endpoint to restart the Splunk Universal Forwarder."

    # POST method: restart Splunk UF
    try:
        # Correct splunk executable path (no trailing >, add splunk.exe)
        splunk_path = r'C:\Program Files\SplunkUniversalForwarder\bin\splunk.exe'
        
        # Command to restart splunk UF
        cmd = f'"{splunk_path}" restart --accept-license --answer-yes'

        # Run the command in shell, capture output
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return jsonify({
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "Splunk UF Restart API is running. Use POST /restart_uf to restart."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
