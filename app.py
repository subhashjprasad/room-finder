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

@app.route('/api/available_rooms', methods=['GET'])
def get_available_rooms():
    day = request.args.get('day')
    time = float(request.args.get('time'))
    duration = float(request.args.get('duration'))
    day_number = day_to_number[day]

    end_time = time + duration
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
        available_rooms_by_building[building] = len(available_room_numbers)

    return jsonify(available_rooms_by_building)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/token')
def get_mapbox_token():
    access_token = os.getenv('MAPBOX_ACCESS_TOKEN')
    return jsonify({'accessToken': access_token})

@app.route('/api/available_rooms')
def available_rooms():
    day = request.args.get('day')
    time = float(request.args.get('time'))
    duration = float(request.args.get('duration'))
    rooms = get_available_rooms(day, time, duration)
    return jsonify(rooms)

if __name__ == '__main__':
    app.run(debug=True)