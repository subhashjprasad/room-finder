from flask import Flask, jsonify, render_template, request
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

app = Flask(__name__)

day_to_number = {"M": 1, "TU": 2, "W": 3, "TH": 4, "F": 5, "SA": 6, "SU": 7}



def create_doc(d, t):
    day = d
    time = t
    day_number = day_to_number[day]

    end_time = time + 0.5
    available_rooms_by_building = {}

    for building in db.list_collection_names():
        collection = db[building]

        query = {
            "occupied_times": {
                "$not": {
                    "$elemMatch": {
                        "$gte": (day_number * 100) + time,  # Start time
                        "$lt": (day_number * 100) + end_time  # End time (exclusive)
                    }
                }
            }
        }
        available_rooms = collection.find(query, {"room_number": 1})
        available_room_numbers = [room["room_number"] for room in available_rooms]
        available_rooms_by_building[building] = available_room_numbers

    dayTimeDocument = {
        "day": day,
        "time": time,
        "data": available_rooms_by_building
    }

    client['dayTime_database']['dayTime_collection'].insert_one(dayTimeDocument)

for d in day_to_number.keys():
    i = 18.0
    while i < 24.0:
        create_doc(d, i)
        i += 0.5