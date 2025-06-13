import requests
import time
import json

ngrok_url = "https://cadc-136-232-205-158.ngrok-free.app/restart_uf"
headers = {"Content-Type": "application/json"}

def trigger_restart(url, retries=3, delay=5):
    for attempt in range(1, retries + 1):
        try:
            print(f"Attempt {attempt}: Sending POST request to restart Universal Forwarder...")
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raises HTTPError for bad status

            data = response.json()

            print("Response from server:")
            print(json.dumps(data, indent=2))  # Pretty print JSON response
            return

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("All retries failed.")

if __name__ == "__main__":
    trigger_restart(ngrok_url)
