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

db = client['dayTime_database']

app = Flask(__name__)

day_to_number = {"M": 1, "TU": 2, "W": 3, "TH": 4, "F": 5, "SA": 6, "SU": 7}

def extract_digits(s):
    digits = ''.join(filter(str.isdigit, s))
    return int(digits) if digits else float('inf')

def combine_common_values(dicts):
    if not dicts:
        return {}

    combined_dict = {}

    for key in dicts[0].keys():
        common_values = set(dicts[0][key])

        for d in dicts[1:]:
            common_values &= set(d[key])

        combined_dict[key] = sorted(list(common_values), key = lambda x: extract_digits(x))

    return combined_dict

@app.route('/api/available_rooms', methods=['GET'])
def get_available_rooms():
    day = request.args.get('day')
    time = float(request.args.get('time'))
    duration = float(request.args.get('duration'))

    end_time = time + duration

    collection = db['dayTime_collection']

    all_available_rooms_by_building = []
    while time < end_time:

        query = {
            "day": day,
            "time": time
        }

        document = collection.find_one(query)

        if document:
            all_available_rooms_by_building.append(document.get('data', {}))

        time += 0.5

    return jsonify(combine_common_values(all_available_rooms_by_building))

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