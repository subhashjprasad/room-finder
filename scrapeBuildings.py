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

db = client['class_database']
collection = db['room_collection']

service = Service(executable_path = "chromedriver.exe")
driver = webdriver.Chrome(service = service)