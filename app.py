import os
import json
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)

# HTML template for the cookie update form
cookie_form_html = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Update Cookies</title>
</head>
<body>
    <h1>Update Lectio Cookies</h1>
    <form method="POST">
        <label for="session_id">ASP.NET_SessionId:</label><br>
        <input type="text" id="session_id" name="ASP.NET_SessionId" required><br><br>

        <label for="autologin_key">autologinkeyV2:</label><br>
        <input type="text" id="autologin_key" name="autologinkeyV2" required><br><br>

        <label for="lectiogsc">lectiogsc:</label><br>
        <input type="text" id="lectiogsc" name="lectiogsc" required><br><br>

        <button type="submit">Update Cookies</button>
    </form>
</body>
</html>
"""

# 1) Update cookies endpoint with UI
@app.route("/update_cookies", methods=["GET", "POST"])
def update_cookies():
    """
    GET: Display a form to input cookies.
    POST: Accept form data and update cookies.json.
    """
    if request.method == "GET":
        return render_template_string(cookie_form_html)

    if request.method == "POST":
        new_cookies = {
            "ASP.NET_SessionId": request.form.get("ASP.NET_SessionId"),
            "autologinkeyV2": request.form.get("autologinkeyV2"),
            "lectiogsc": request.form.get("lectiogsc")
        }

        if not all(new_cookies.values()):
            return jsonify({"error": "All fields are required"}), 400

        # Overwrite cookies.json
        try:
            with open("cookies.json", "w", encoding="utf-8") as f:
                json.dump(new_cookies, f, indent=2)
            return jsonify({"status": "Cookies updated successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# 2) Serve ICS file(s)
@app.route("/ics/<path:filename>")
def serve_ics(filename):
    """
    Serve any .ics file from the ics_files folder.
    e.g. GET /ics/lectio_subscription.ics
    """
    ics_dir = os.path.join(app.root_path, "ics_files")
    return send_from_directory(ics_dir, filename)


if __name__ == "__main__":
    # WARNING: Running on port 80 often requires root or special permissions.
    # For testing or Docker, you can do app.run(host="0.0.0.0", port=80, debug=False)
    # or consider using port 5000 behind Nginx if you want production readiness.
    app.run(host="0.0.0.0", port=80, debug=False)