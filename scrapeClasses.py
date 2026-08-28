from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import re
import time
import logging
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("scrape.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

password = os.environ.get("DB_PASSWORD")

uri = "mongodb+srv://subhashjprasad:" + password + "@cluster.mtb0pln.mongodb.net/?retryWrites=true&w=majority&appName=CLUSTER"
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client['building_database']

driver = webdriver.Chrome()

wait_time = 10

# Site now uses Mo/Tu/We/Th/Fr/Sa/Su abbreviations
day_to_number = {"Mo": 1, "Tu": 2, "We": 3, "Th": 4, "Fr": 5, "Sa": 6, "Su": 7}


def parse_time_to_decimal(time_str):
    """Parse '01:00 pm' or '1:00pm' to a decimal hour (13.0 for 1:00pm)."""
    s = time_str.strip().lower().replace(" ", "")
    m = re.match(r'^(\d{1,2}):(\d{2})(am|pm)$', s)
    if not m:
        return None
    hour, minute, period = int(m.group(1)), int(m.group(2)), m.group(3)
    if period == 'pm' and hour != 12:
        hour += 12
    elif period == 'am' and hour == 12:
        hour = 0
    return hour + minute / 60.0


def write_timeslots(collection, room, timeslots):
    for slot in timeslots:
        try:
            doc = collection.find_one({"room_number": room})
            if doc:
                times = list(doc.get("occupied_times", []))
                times.append(slot)
                collection.update_one({"_id": doc["_id"]}, {"$set": {"occupied_times": times}})
            else:
                collection.insert_one({"room_number": room, "occupied_times": [slot]})
        except Exception as e:
            log.warning("MongoDB write failed for %s slot %s: %s", room, slot, e)


def parse_timeslots(class_time_str, class_days_str, context):
    """Return list of numeric timeslots, or None on any parse error."""
    parts = re.split(r'\s*-\s*', class_time_str, maxsplit=1)
    if len(parts) < 2:
        log.warning("SKIP %s: time has no hyphen: %r", context, class_time_str)
        return None

    start = parse_time_to_decimal(parts[0])
    end = parse_time_to_decimal(parts[1])
    if start is None or end is None:
        log.warning("SKIP %s: unparseable time: %r", context, class_time_str)
        return None

    start_half = round(start * 2)
    end_half = round(end * 2)
    half_hours = [i / 2 for i in range(start_half, end_half)]

    timeslots = []
    for day in [d.strip() for d in class_days_str.split(",")]:
        if day not in day_to_number:
            log.warning("SKIP %s: unrecognised day: %r", context, day)
            return None
        timeslots.extend([(day_to_number[day] * 100) + t for t in half_hours])

    return timeslots


def extract_meeting_info(container, context):
    """Pull days/time/location text out of an sf--meeting-* container."""
    try:
        days_el = container.find_element(By.CLASS_NAME, "sf--meeting-days")
        spans = days_el.find_elements(By.TAG_NAME, "span")
        class_days = next(
            (s.text.strip() for s in spans if "icon" not in (s.get_attribute("class") or "")),
            ""
        )
    except Exception as e:
        log.warning("SKIP %s: could not read meeting days: %s", context, e)
        return None, None, None

    try:
        time_el = container.find_element(By.CLASS_NAME, "sf--meeting-time")
        spans = time_el.find_elements(By.TAG_NAME, "span")
        class_time = next(
            (s.text.strip() for s in spans if "icon" not in (s.get_attribute("class") or "")),
            ""
        )
    except Exception as e:
        log.warning("SKIP %s: could not read meeting time: %s", context, e)
        return None, None, None

    try:
        loc_el = container.find_element(By.CLASS_NAME, "sf--location")
        # Room name is either a direct text node or the first text node inside a map <a> link.
        # Never use full textContent/innerText — the <a> contains an SVG with "(link is external)".
        class_location = driver.execute_script("""
            var el = arguments[0];
            var direct = [...el.childNodes]
                .filter(n => n.nodeType === 3 && n.textContent.trim())
                .map(n => n.textContent.trim())
                .join(' ');
            if (direct) return direct;
            var a = el.querySelector('a');
            if (a) {
                var t = [...a.childNodes].find(n => n.nodeType === 3 && n.textContent.trim());
                return t ? t.textContent.trim() : null;
            }
            return null;
        """, loc_el)
    except Exception as e:
        log.warning("SKIP %s: could not read location: %s", context, e)
        return None, None, None

    return class_days, class_time, class_location


def process_meeting(class_days, class_time, class_location, context):
    """Validate fields, parse timeslots, and write to MongoDB."""
    if not class_days or not class_time or not class_location:
        log.warning("SKIP %s: empty field — days=%r time=%r location=%r", context, class_days, class_time, class_location)
        return

    timeslots = parse_timeslots(class_time, class_days, context)
    if timeslots is None:
        return

    room = class_location.strip()
    parts = room.split()
    if not parts:
        log.warning("SKIP %s: blank location", context)
        return
    parts.pop()
    building = ' '.join(parts)

    if not building:
        log.warning("SKIP %s: could not determine building from %r", context, room)
        return

    if building == "HAAS Faculty Wing":
        building = "Haas Faculty Wing"
    if building == "Rec Sports Facility":
        building = "RSF"

    try:
        collection = db[building]
        collection.create_index([("occupied_times", 1)])
    except Exception as e:
        log.warning("SKIP %s: MongoDB setup failed for %r: %s", context, building, e)
        return

    write_timeslots(collection, room, timeslots)


def get_class_information(url):
    driver.get(url)

    # --- Lecture ---
    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "sf--meetings"))
        )
        meeting_el = driver.find_element(By.CLASS_NAME, "sf--meetings")
    except TimeoutException:
        log.warning("SKIP %s: timeout waiting for sf--meetings", url)
        return

    days, t, loc = extract_meeting_info(meeting_el, url)
    process_meeting(days, t, loc, url)

    # --- Sections (JS-rendered inside detail-class-associated-sections) ---
    try:
        section_container = driver.find_element(By.CLASS_NAME, "detail-class-associated-sections")
        WebDriverWait(driver, wait_time).until(
            lambda d: section_container.find_elements(By.CLASS_NAME, "sf--meeting-days")
        )
        section_meetings = section_container.find_elements(By.CLASS_NAME, "sf--meetings")
    except (TimeoutException, NoSuchElementException):
        return  # no sections is normal
    except Exception as e:
        log.warning("SKIP sections for %s: %s", url, e)
        return

    for i, section_el in enumerate(section_meetings):
        ctx = f"{url} section[{i}]"
        days, t, loc = extract_meeting_info(section_el, ctx)
        process_meeting(days, t, loc, ctx)


def restart_driver():
    global driver
    try:
        driver.quit()
    except Exception:
        pass
    driver = webdriver.Chrome()
    log.warning("Chrome restarted")


def is_session_dead(e):
    msg = str(e).lower()
    return any(s in msg for s in [
        "invalid session id", "session deleted", "no such session",
        "err_internet_disconnected", "err_connection_refused"
    ])

def navigate_with_retry(url, label, max_attempts=5):
    """Navigate to url, restarting Chrome on session death. Returns True on success."""
    for attempt in range(max_attempts):
        try:
            driver.get(url)
            return True
        except WebDriverException as e:
            if is_session_dead(e):
                log.warning("Chrome session died on %s (attempt %d) — restarting", label, attempt + 1)
                restart_driver()
                time.sleep(5 * (attempt + 1))  # back off before retry
            else:
                log.warning("WebDriverException on %s: %s", label, e)
                return False
    log.warning("Giving up on %s after %d attempts", label, max_attempts)
    return False


BASE_URL = "https://classes.berkeley.edu/search/class?f%5B0%5D=term%3A8588"
page = 299  # resume from page 299 (0-indexed)
page_limit = 339 - 299

while page_limit > 0:
    # Restart Chrome every 50 pages to prevent memory-induced tab crashes
    if page > 0 and page % 50 == 0:
        restart_driver()

    page_url = BASE_URL if page == 0 else f"{BASE_URL}&page={page}"
    page += 1
    page_limit -= 1

    if not navigate_with_retry(page_url, f"page {page}"):
        continue

    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, "//a[starts-with(@href, '/content/')]"))
        )
        class_elements = driver.find_elements(By.XPATH, "//a[starts-with(@href, '/content/')]")
        class_urls = list(set(e.get_attribute("href") for e in class_elements))
    except TimeoutException:
        log.warning("No class links on page %d — stopping", page)
        break

    log.warning("Page %d: found %d classes", page, len(class_urls))

    for u in class_urls:
        try:
            get_class_information(u)
        except WebDriverException as e:
            if is_session_dead(e):
                log.warning("Chrome session died on %s — restarting", u)
                restart_driver()
                time.sleep(10)
            else:
                log.warning("WebDriverException on %s: %s", u, e)

time.sleep(5)

driver.quit()
