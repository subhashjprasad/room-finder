from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

password = os.environ.get("DB_PASSWORD")

uri = "mongodb+srv://subhashjprasad:" + password + "@cluster.mtb0pln.mongodb.net/?retryWrites=true&w=majority&appName=CLUSTER"
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client['building_database']

service = Service(executable_path = "chromedriver.exe")
driver = webdriver.Chrome(service = service)

wait_time = 2

time_string_to_number = {
    "12:00am": 0.0, "12:29am": 0.5, "12:30am": 0.5, "12:59am": 1.0,
    "1:00am": 1.0, "1:29am": 1.5, "1:30am": 1.5, "1:59am": 2.0,
    "2:00am": 2.0, "2:29am": 2.5, "2:30am": 2.5, "2:59am": 3.0,
    "3:00am": 3.0, "3:29am": 3.5, "3:30am": 3.5, "3:59am": 4.0,
    "4:00am": 4.0, "4:29am": 4.5, "4:30am": 4.5, "4:59am": 5.0,
    "5:00am": 5.0, "5:29am": 5.5, "5:30am": 5.5, "5:59am": 6.0,
    "6:00am": 6.0, "6:29am": 6.5, "6:30am": 6.5, "6:59am": 7.0,
    "7:00am": 7.0, "7:29am": 7.5, "7:30am": 7.5, "7:59am": 8.0,
    "8:00am": 8.0, "8:29am": 8.5, "8:30am": 8.5, "8:59am": 9.0,
    "9:00am": 9.0, "9:29am": 9.5, "9:30am": 9.5, "9:59am": 10.0,
    "10:00am": 10.0, "10:29am": 10.5, "10:30am": 10.5, "10:59am": 11.0,
    "11:00am": 11.0, "11:29am": 11.5, "11:30am": 11.5, "11:59am": 12.0,
    "12:00pm": 12.0, "12:29pm": 12.5, "12:30pm": 12.5, "12:59pm": 13.0,
    "1:00pm": 13.0, "1:29pm": 13.5, "1:30pm": 13.5, "1:59pm": 14.0,
    "2:00pm": 14.0, "2:29pm": 14.5, "2:30pm": 14.5, "2:59pm": 15.0,
    "3:00pm": 15.0, "3:29pm": 15.5, "3:30pm": 15.5, "3:59pm": 16.0,
    "4:00pm": 16.0, "4:29pm": 16.5, "4:30pm": 16.5, "4:59pm": 17.0,
    "5:00pm": 17.0, "5:29pm": 17.5, "5:30pm": 17.5, "5:59pm": 18.0,
    "6:00pm": 18.0, "6:29pm": 18.5, "6:30pm": 18.5, "6:59pm": 19.0,
    "7:00pm": 19.0, "7:29pm": 19.5, "7:30pm": 19.5, "7:59pm": 20.0,
    "8:00pm": 20.0, "8:29pm": 20.5, "8:30pm": 20.5, "8:59pm": 21.0,
    "9:00pm": 21.0, "9:29pm": 21.5, "9:30pm": 21.5, "9:59pm": 22.0,
    "10:00pm": 22.0, "10:29pm": 22.5, "10:30pm": 22.5, "10:59pm": 23.0,
    "11:00pm": 23.0, "11:29pm": 23.5, "11:30pm": 23.5, "11:59pm": 0.0
}

day_to_number = {"M": 1, "TU": 2, "W": 3, "TH": 4, "F": 5, "SA": 6, "SU": 7}

def get_class_information(url):
    driver.get(url)

    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "detail-days"))
        )
        class_days = driver.find_element(By.CLASS_NAME, "detail-days").text
    except TimeoutException:
        return

    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "detail-time"))
        )
        class_time = driver.find_element(By.CLASS_NAME, "detail-time").text
    except TimeoutException:
        return

    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "detail-location"))
        )
        class_location = driver.find_element(By.CLASS_NAME, "detail-location").text
    except TimeoutException:
        return

    class_time = class_time.split("-")
    class_time = [string.replace(" ", "") for string in class_time]
    class_time_start = time_string_to_number[class_time[0]]
    class_time_end = time_string_to_number[class_time[1]]

    class_times = []
    current_time = class_time_start

    while current_time < class_time_end:
        class_times.append(current_time)
        current_time += 0.5

    if len(class_days) == 0 or len(class_time) == 0 or len(class_location) == 0: return

    class_days = class_days.split(", ")
    class_days = [string.replace(" ", "") for string in class_days]

    class_timeslots = []
    for class_day in class_days:
        class_timeslots.extend([(day_to_number[class_day] * 100) + class_time for class_time in class_times])

    class_location_text_cut = class_location.replace("\n(opens in a new tab)", "")

    parts = class_location_text_cut.split()
    parts.pop()
    class_building = ' '.join(parts)

    if len(class_building) == 0: return
    collection = db[class_building]
    collection.create_index([("occupied_times", 1)])

    for class_timeslot in class_timeslots:
        room_document = collection.find_one({"room_number": class_location_text_cut})
        if room_document:
            existing_occupied_times = list(room_document.get("occupied_times", []))
            existing_occupied_times.append(class_timeslot)
            collection.update_one(
                {"_id": room_document["_id"]},
                {"$set": {"occupied_times": existing_occupied_times}}
            )
        else:
            room_document = {
                "room_number": class_location_text_cut,
                "occupied_times": [class_timeslot]
            }
            collection.insert_one(room_document)


next_page = "https://classes.berkeley.edu/search/class/?f%5B0%5D=im_field_term_name%3A3151"
page_limit = 10

while (next_page is not None and page_limit > 0):
    driver.get(next_page)
    page_limit -= 1
    
    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ls-section-wrapper"))
        )
        classes = driver.find_elements(By.CLASS_NAME, "ls-section-wrapper")
        class_urls = [c.get_attribute("href") for c in classes]
    except TimeoutException:
        class_urls = []
    
    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "pager-next"))
        )
        next_page = driver.find_element(By.CLASS_NAME, "pager-next").find_element(By.TAG_NAME, "a").get_attribute("href")
    except TimeoutException:
        next_page = None

    for u in class_urls:
        get_class_information(u)

time.sleep(5)

driver.quit()