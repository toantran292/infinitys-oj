from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
LOG_FILE = "webhook_log.json"


@app.route("/", methods=["POST"])
def receive_webhook():
    data = request.json

    print("📩 Webhook Received:")
    print(json.dumps(data, indent=2))

    # Append to log file
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(data)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    return jsonify({"status": "received"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9999)
