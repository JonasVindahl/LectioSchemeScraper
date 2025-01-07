import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/update_cookies", methods=["POST"])
def update_cookies():
    """
    Expects JSON like:
    {
      "ASP.NET_SessionId": "...",
      "autologinkeyV2": "...",
      "lectiogsc": "...",
      ...
    }
    """
    new_cookies = request.json
    if not new_cookies:
        return jsonify({"error": "No JSON data"}), 400
    
    try:
        with open("cookies.json", "w", encoding="utf-8") as f:
            json.dump(new_cookies, f, indent=2)
        return jsonify({"status": "Cookies updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)