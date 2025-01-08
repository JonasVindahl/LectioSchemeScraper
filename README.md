---

# Lectio Schedule Scraper and ICS Server

This project automates fetching a schedule from Lectio.dk and provides:
- A Python script (`GetSkema.py`) that scrapes the Lectio schedule and generates an ICS file.
- A Flask web server (`app.py`) that:
  - Serves the ICS file.
  - Allows remote updates of cookies via a web UI.
  - Optionally triggers the scraper manually.
- Automated setup using `systemd` to run the Flask server and periodically run the scraper.
- Optional Pushover notifications to alert on failures (such as expired cookies or empty schedules).

---

## General Information

### Cookie Management
- **Cookies are essential for fetching schedules from Lectio.** If cookies expire, you need to update them using the provided web UI (`/cookies`) or through an API request.
- Keep the `cookies.json` file secure, as it contains sensitive login information.

### ICS File Accessibility
- The generated ICS file is publicly accessible to anyone with the URL. If privacy is a concern, consider adding authentication to the Flask server or using a randomized or unique filename for the ICS file.

### Pushover Notifications (Optional)
- Pushover notifications can be enabled to receive alerts if the scraper encounters issues, such as:
  - Being redirected to the login page (indicating expired cookies).
  - An empty schedule being fetched.
- To enable Pushover, you need to set the `PUSHOVER_API_KEY` and `PUSHOVER_USER_KEY` in `GetSkema.py`.

---

## 1. Prerequisites

### Server Requirements
- Ubuntu Server (20.04+ or 22.04+)
- Python 3.8+

### Installation Commands

1. **Update your package list and install Python:**

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv
   ```

2. **Clone the repository:**

   ```bash
   git clone https://github.com/JonasVindahl/LectioSchemeScraper.git
   cd LectioSchemeScraper
   ```

3. **Create a virtual environment and install dependencies:**

   ```bash
   python3 -m venv lectio-venv
   source lectio-venv/bin/activate
   pip install -r requirements.txt
   ```

---

## 2. Automate with Systemd

### 2.1 Flask Server Service

This `systemd` service will keep the Flask server running, which serves the ICS file and handles cookie updates.

1. **Create the service file `/etc/systemd/system/lectio-flask.service`:**

   ```bash
   sudo nano /etc/systemd/system/lectio-flask.service
   ```

   Paste the following content:

   ```ini
   [Unit]
   Description=Lectio Flask Server
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/root/LectioSchemeScraper
   ExecStart=/root/LectioSchemeScraper/lectio-venv/bin/python /root/LectioSchemeScraper/app.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and start the Flask server service:**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable lectio-flask.service
   sudo systemctl start lectio-flask.service
   ```

3. **Verify that the Flask server is running:**

   ```bash
   sudo systemctl status lectio-flask.service
   ```

The Flask server should now be accessible on port `80`. You can subscribe to your calendar at:

```
http://<server-ip>/ics/lectio_subscription.ics
```

---

### 2.2 Scraper Service (Every 10 Minutes)

This `systemd` service will run the scraper every 10 minutes to update the ICS file.

1. **Create the service file `/etc/systemd/system/lectio-scraper.service`:**

   ```bash
   sudo nano /etc/systemd/system/lectio-scraper.service
   ```

   Paste the following content:

   ```ini
   [Unit]
   Description=Lectio Scraper Service
   After=network.target

   [Service]
   Type=oneshot
   User=root
   WorkingDirectory=/root/LectioSchemeScraper
   ExecStart=/root/LectioSchemeScraper/lectio-venv/bin/python /root/LectioSchemeScraper/GetSkema.py

   [Install]
   WantedBy=multi-user.target
   ```

2. **Create the timer file `/etc/systemd/system/lectio-scraper.timer`:**

   ```bash
   sudo nano /etc/systemd/system/lectio-scraper.timer
   ```

   Paste the following content:

   ```ini
   [Unit]
   Description=Run the Lectio Scraper every 10 minutes

   [Timer]
   OnBootSec=1min
   OnUnitActiveSec=10min
   Unit=lectio-scraper.service

   [Install]
   WantedBy=timers.target
   ```

3. **Enable and start the timer:**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable lectio-scraper.timer
   sudo systemctl start lectio-scraper.timer
   ```

4. **Check the timer status:**

   ```bash
   sudo systemctl status lectio-scraper.timer
   ```

You can view the logs for the scraper with:

```bash
sudo journalctl -u lectio-scraper.service -f
```

---

## 3. Cookie Management UI

You can update the cookies using the built-in web UI:

1. **Visit the cookie management page in your browser:**

   ```
   http://<server-ip>/cookies
   ```

2. **Enter your new cookies in the provided form and submit.**

---

## 4. iPhone Calendar Subscription

On your iPhone:

1. Go to `Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar`.
2. Enter the URL:

   ```
   http://<server-ip>/ics/lectio_subscription.ics
   ```

3. Confirm and set the desired refresh interval.

---

## 5. Troubleshooting

### Flask server not starting:
Check the logs with:

```bash
sudo journalctl -u lectio-flask.service -f
```

### Scraper not running:
Ensure the timer is active:

```bash
sudo systemctl list-timers --all | grep lectio-scraper
```

### Cookie expiration:
If the schedule stops updating, it likely means the cookies have expired. Update the cookies using the `/cookies` web UI.

---