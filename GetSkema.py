import os
import json
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import uuid
import hashlib

# Pushover Configuration (Set your keys here)
PUSHOVER_ENABLED = True  # Set to False to disable notifications
PUSHOVER_API_KEY = "your-pushover-api-key"
PUSHOVER_USER_KEY = "your-pushover-user-key"

#
# 1. Load cookies from a local JSON file
#
def load_cookies():
    """Load cookies from cookies.json file."""
    with open("cookies.json", "r", encoding="utf-8") as f:
        return json.load(f)

#
# 2. Send Pushover notification (optional)
#
def send_pushover_notification(title, message):
    """Send a Pushover notification if enabled."""
    if not PUSHOVER_ENABLED:
        return
    data = {
        "token": PUSHOVER_API_KEY,
        "user": PUSHOVER_USER_KEY,
        "title": title,
        "message": message,
    }
    try:
        response = requests.post("https://api.pushover.net/1/messages.json", data=data)
        if response.status_code == 200:
            print("Pushover notification sent.")
        else:
            print(f"Failed to send Pushover notification. HTTP {response.status_code}")
    except Exception as e:
        print(f"Error sending Pushover notification: {e}")

#
# 3. Fetch the Lectio page
#
def fetch_lectio_schedule(week, year):
    """Fetch the Lectio schedule page."""
    c = load_cookies()
    cookies = {
        "ASP.NET_SessionId": c.get("ASP.NET_SessionId", ""),
        "autologinkeyV2": c.get("autologinkeyV2", ""),
        "lectiogsc": c.get("lectiogsc", "")
    }

    url = f"https://www.lectio.dk/lectio/518/SkemaNy.aspx?week={week}{year}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, cookies=cookies)

    if response.status_code == 200:
        if "Log ind" in response.text or "Du er ikke logget ind" in response.text:
            send_pushover_notification(
                "Lectio Scraper Error",
                f"Scraper was redirected to login page for week {week}, year {year}. Cookies may have expired."
            )
            print(f"Redirection detected. Cookies may have expired.")
            return None
        return response.text
    else:
        send_pushover_notification(
            "Lectio Scraper Error",
            f"Failed to fetch schedule for week {week}, year {year}. HTTP {response.status_code}."
        )
        print(f"Failed to fetch week {week}, year {year}. HTTP {response.status_code}")
        return None

#
# 4. Parse out events (same as before)
#
def parse_schedule(html):
    soup = BeautifulSoup(html, "html.parser")

    # Default module times
    default_module_times = {
        "M1":  (8, 15, 9, 0),
        "M2":  (9, 0, 9, 45),
        "M3":  (10, 0, 10, 45),
        "M4":  (10, 45, 11, 30),
        "M5":  (12, 0, 12, 45),
        "M6":  (12, 45, 13, 30),
        "M7":  (13, 30, 14, 15),
        "M8":  (14, 30, 15, 15),
        "M9":  (15, 15, 16, 0),
        "M10": (16, 0, 16, 45),
    }

    def parse_date(datestr):
        match = re.match(r"(\d{1,2})/(\d{1,2})-(\d{4})", datestr)
        if match:
            d, m, y = match.groups()
            return datetime(int(y), int(m), int(d))
        return None

    def parse_time(timestr):
        hh, mm = timestr.split(":")
        return int(hh), int(mm)

    events = []

    # For each day <td data-date="YYYY-MM-DD">
    day_tds = soup.find_all("td", {"data-date": True})
    for td in day_tds:
        day_str = td["data-date"]
        day_date = datetime.strptime(day_str, "%Y-%m-%d").date()

        # Each "lesson" block is an <a class="s2skemabrik">
        bricks = td.find_all("a", class_="s2skemabrik")

        for brick in bricks:
            if "s2cancelled" in brick.get("class", []):
                continue

            if "s2infoHeader" in brick.get("class", []):
                continue
            parent_info = brick.find_parent("div", class_="s2infoHeader")
            if parent_info is not None:
                continue

            tooltip = brick.get("data-tooltip", "")
            lines = tooltip.strip().split("\n")

            # Try to parse date/time from the tooltip
            date_time_pattern = re.compile(
                r"(\d{1,2}/\d{1,2}-\d{4})\s+(\d{1,2}:\d{2})\s+til\s+(\d{1,2}:\d{2})"
            )
            match_time = date_time_pattern.search(tooltip)

            start_dt = None
            end_dt   = None
            location = ""

            if match_time:
                date_str_tt = match_time.group(1)
                start_time_str = match_time.group(2)
                end_time_str   = match_time.group(3)

                dt_date = parse_date(date_str_tt)
                if dt_date:
                    s_hh, s_mm = parse_time(start_time_str)
                    e_hh, e_mm = parse_time(end_time_str)
                    start_dt = dt_date.replace(hour=s_hh, minute=s_mm)
                    end_dt   = dt_date.replace(hour=e_hh, minute=e_mm)
                else:
                    s_hh, s_mm = parse_time(start_time_str)
                    e_hh, e_mm = parse_time(end_time_str)
                    start_dt = datetime(day_date.year, day_date.month, day_date.day, s_hh, s_mm)
                    end_dt   = datetime(day_date.year, day_date.month, day_date.day, e_hh, e_mm)
            else:
                module_match = brick.parent.find("div", {"data-module": True})
                if module_match:
                    module_id = module_match["data-module"]
                    if module_id in default_module_times:
                        s_hh, s_mm, e_hh, e_mm = default_module_times[module_id]
                        start_dt = datetime(day_date.year, day_date.month, day_date.day, s_hh, s_mm)
                        end_dt   = datetime(day_date.year, day_date.month, day_date.day, e_hh, e_mm)
            if not start_dt:
                continue

            real_title = None
            s2content = brick.select_one(".s2skemabrikcontent")
            if s2content:
                title_span = s2content.select_one('span[style*="word-wrap:break-word"]')
                if title_span:
                    text_found = title_span.get_text(strip=True)
                    if text_found:
                        real_title = text_found

            hold_text = ""
            teacher_text = ""
            other_description_lines = []

            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue
                if line_str.lower().startswith("lokale:"):
                    location = line_str.split(":", 1)[1].strip()
                elif line_str.lower().startswith("hold:"):
                    hold_text = line_str.split(":", 1)[1].strip()
                elif line_str.lower().startswith("lærer:"):
                    teacher_text = line_str.split(":", 1)[1].strip()
                other_description_lines.append(line_str)

            if real_title:
                summary = real_title
            else:
                if hold_text or teacher_text:
                    summary = " | ".join([t for t in (hold_text, teacher_text) if t])
                else:
                    summary = "Lectio event"

            description_text = "\n".join(other_description_lines)

            events.append({
                "start_dt": start_dt,
                "end_dt": end_dt,
                "summary": summary,
                "location": location,
                "description": description_text
            })

    return events

#
# Generate persistent UIDs
#
def generate_uid(event):
    uid_str = f"{event['start_dt']}{event['end_dt']}{event['summary']}{event['location']}"
    return hashlib.sha256(uid_str.encode("utf-8")).hexdigest()[:16] + "@lectio"

#
# ICS building with persistent UIDs
#
def events_to_ics(events, output_filename):
    now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    ics_lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//My Lectio Parser//EN"]
    
    for evt in events:
        uid_str = generate_uid(evt)
        start_str = evt["start_dt"].strftime("%Y%m%dT%H%M%S")
        end_str   = evt["end_dt"].strftime("%Y%m%dT%H%M%S")

        ics_lines.append("BEGIN:VEVENT")
        ics_lines.append(f"UID:{uid_str}")
        ics_lines.append(f"DTSTAMP:{now_str}")
        ics_lines.append(f"DTSTART:{start_str}")
        ics_lines.append(f"DTEND:{end_str}")
        ics_lines.append(f"SUMMARY:{escape_ics_text(evt['summary'])}")
        if evt["location"]:
            ics_lines.append(f"LOCATION:{escape_ics_text(evt['location'])}")
        if evt["description"]:
            ics_lines.append(f"DESCRIPTION:{escape_ics_text(evt['description'])}")
        ics_lines.append("END:VEVENT")

    ics_lines.append("END:VCALENDAR")

    ics_folder = "ics_files"
    if not os.path.exists(ics_folder):
        os.makedirs(ics_folder)

    final_path = os.path.join(ics_folder, output_filename)
    with open(final_path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(ics_lines))
    print(f"Created ICS: {final_path}")

def escape_ics_text(text):
    return (
        text.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
    )

#
# Main (Example usage)
#
if __name__ == "__main__":
    # 1) Get the current ISO week & year
    today = datetime.now()
    iso_year, iso_week, _ = today.isocalendar()

    all_events = []

    # 2) Scrape the next 15 weeks
    for i in range(15):
        w = iso_week + i
        y = iso_year
        if w > 53:
            w -= 53
            y += 1
        week_str = f"{w:02d}"
        
        print(f"Fetching schedule for week={week_str}, year={y}...")
        html_text = fetch_lectio_schedule(week_str, str(y))
        
        if html_text:
            weekly_events = parse_schedule(html_text)
            if not weekly_events:  # Check if parsing returned empty
                send_pushover_notification(
                    "Lectio Scraper Warning",
                    f"No events found for week {week_str}, year {y}. The page may be empty."
                )
            all_events.extend(weekly_events)

    # 3) Generate ICS if there are events
    if all_events:
        ics_file = "lectio_subscription.ics"
        events_to_ics(all_events, ics_file)
    else:
        send_pushover_notification(
            "Lectio Scraper Error",
            "No events found for any of the weeks. Check if cookies have expired or if there are other issues."
        )