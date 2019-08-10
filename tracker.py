# -*- coding: utf-8 -*-
from flask import Flask, render_template, request
from flask_httpauth import HTTPBasicAuth
import logging
import hashlib
from pymongo import MongoClient
import pymongo
import simplejson as json
from passwords import users
from config import options
from datetime import datetime
import time
import base64
import twitter_interface

# Create app and configure logging
app = Flask(__name__)
auth = HTTPBasicAuth()
LOG_FILENAME = '/tmp/flask-errores.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)
app.logger.debug("Arranque de la app")
app.insert_counter = 0  # for twitts

# twitter interface
tweets = twitter_interface.TwitterInterface(options)

# HTTPBasicAuth, returns hashed password
@auth.hash_password
def hash_pw(password):
    return hashlib.md5(password).hexdigest()

# HTTPBasicAuth, gets password from users database
@auth.get_password
def get_pw(username):
    app.logger.debug('user %s', username)
    if username in users:
        return users.get(username)
    return None

# HTTPBasicAuth, failed authentication
@auth.error_handler
def auth_error():
    app.logger.debug("Fallo de autentificación")
    return "No puedes pasar!\n"

# Telemetry main webpage
@app.route('/')
def hello_world():
    return render_template('index.html', config=options)


@app.route('/test')
@auth.login_required
def test():
    return "Hello, %s!\n" % auth.username()

# Webservices
# get data from mongodb by ID
@app.route('/get/<int:id>')
def get_id(id):
    # connect to mongoDB and query database for ID
    mongo_client = MongoClient(options["mongo_host"], options["mongo_port"])
    mongo_db = mongo_client[options["mongo_db"]]
    mongo_collection = mongo_db[options["mongo_col"]]
    document = mongo_collection.find_one({"_id": str(id)})

    # return JSON
    return json.dumps(document, sort_keys=True)

# get last data added to the mongodb
@app.route('/get/last')
def get_last():
    # connect to mongoDB and query database
    mongo_client = MongoClient(options["mongo_host"], options["mongo_port"])
    mongo_db = mongo_client[options["mongo_db"]]
    mongo_collection = mongo_db[options["mongo_col"]]
    # order new first and get the first one
    cursor = mongo_collection.find().sort("_id", pymongo.DESCENDING).limit(1)
    telem = cursor[0]

    # convert coordinates (+/-)
    if telem["lat"][len(telem["lat"])-1] == 'S':
        telem["lat"] = "-" + telem["lat"][0:len(telem["lat"])-1].lstrip("0")
    else:
        telem["lat"] = telem["lat"][0:len(telem["lat"])-1].lstrip("0")

    if telem["lon"][len(telem["lon"])-1] == 'W':
        telem["lon"] = "-" + telem["lon"][0:len(telem["lon"])-1].lstrip("0")
    else:
        telem["lon"] = telem["lon"][0:len(telem["lon"])-1].lstrip("0")

    # return JSON
    return json.dumps(telem, sort_keys=True)

# get altitude array for graphs
@app.route('/get/alt')
def get_alt():
    # connect to mongoDB and query database
    mongo_client = MongoClient(options["mongo_host"], options["mongo_port"])
    mongo_db = mongo_client[options["mongo_db"]]
    mongo_collection = mongo_db[options["mongo_col"]]
    cursor = mongo_collection.find()

    # get array of altitudes
    data = []
    for doc in cursor:
        data.append(doc["alt"])

    # return JSON
    return json.dumps(data)

# get all data
@app.route('/get')
def get_all():
    # connect to mongoDB and query database
    mongo_client = MongoClient(options["mongo_host"], options["mongo_port"])
    mongo_db = mongo_client[options["mongo_db"]]
    mongo_collection = mongo_db[options["mongo_col"]]
    cursor = mongo_collection.find()

    # get array of all data
    data = []
    for doc in cursor:
        # convert coordinates (+/-)
        if doc["lat"][len(doc["lat"])-1] == 'S':
            doc["lat"] = "-" + doc["lat"][0:len(doc["lat"])-1].lstrip("0")
        else:
            doc["lat"] = doc["lat"][0:len(doc["lat"])-1].lstrip("0")

        if doc["lon"][len(doc["lon"])-1] == 'W':
            doc["lon"] = "-" + doc["lon"][0:len(doc["lon"])-1].lstrip("0")
        else:
            doc["lon"] = doc["lon"][0:len(doc["lon"])-1].lstrip("0")

        data.append(doc)

    # return JSON
    return json.dumps(data, sort_keys=True)

# inserts telemetry in database
def insert_telemetry(telem):
    # check telemetry (dict 13 elements)
    if len(telem) < 12:
        return "Error, not enough fields"
    # add the _id (timestamp with microseconds)
    telem["_id"] = str(int(time.mktime(datetime.now().timetuple())*1000000))
    # connect to mongoDB and select database and collection
    mongo_client = MongoClient(options["mongo_host"], options["mongo_port"])
    mongo_db = mongo_client[options["mongo_db"]]
    mongo_collection = mongo_db[options["mongo_col"]]
    # insert data
    return mongo_collection.insert(telem)


# upload
@app.route('/upload', methods=['POST', 'GET'])
@auth.login_required
def upload():
    # post or get ?
    if request.method == 'POST':
        # image?
        if 'image' in request.args:
            # we have a image in the post data
            # get name from url parameters
            name = request.args.get('image')

            if name != "":
                image = open(options['ssdv_path'] + name, "w")
                image.write(request.get_data().decode('base64'))
                image.close()

                last = open(options['ssdv_path'] + "last.jpg", "w")
                last.write(request.get_data().decode('base64'))
                last.close()

                # tweet?
                if options['twitter_enabled']:
                    tweets.tweet_image(options['ssdv_path'] + "last.jpg")

                return "uploaded image: " + name + ".\n"
            else:
                return "error uploading image"

        # telemetry?
        elif request.form['telemetry'] != "":
            # return "detected telemetry.\n" + request.form['telemetry'] + "\n"
            # get data
            data = request.form['telemetry'].split(";")
            # create dictionary
            telemetry = {
                'date' : data[0],
                'time' : data[1],
                'lat'  : data[2],
                'lon'  : data[3],
                'alt'  : data[4],
                'batt' : data[5],
                'tin'  : data[6],
                'tout' : data[7],
                'baro' : data[8],
                'hdg'  : data[9],
                'spd'  : data[10],
                'sats' : data[11],
                'a_rate' : data[12]
            }
            # insert data
            inserted = insert_telemetry(telemetry)

            # tweet?
            if options['twitter_enabled']:
                if app.insert_counter == 0:
                    tweets.tweet_telemetry(telemetry)
                app.insert_counter += 1
                if app.insert_counter > options['twitter_interval']:
                    app.insert_counter = 0

            return inserted
        else:
            return "nothing detected!\n"
    else:
        return "what?\n"

######### MAIN ##########
if __name__ == '__main__':
    app.run(debug=True)

