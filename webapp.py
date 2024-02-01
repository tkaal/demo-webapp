from flask import Flask

from flask import request

from waitress import serve

import psycopg2

import json

import os

from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)

conn = psycopg2.connect(
        host=os.environ.get('DBHOST'),
        database=os.environ.get('DB'),
        user=os.environ.get('DBUSER'),
        password=os.environ.get('DBPASS')
        )

@app.route("/")
def info():
    return "Hello there! Demo web app is alive! \n"


@app.route("/insert-item", methods=['POST'])
def insert_item():
    try:
        app.logger.info("Received a POST request for adding a new item to the monitoring table with following data: " + json.dumps(request.json))
        if insert_query(request.json['appname']):
            app.logger.info("Successfully performed the INSERT query!")
            return f"Successfully added new application {request.json['appname']} to monitoring table! \n"
        app.logger.error(f"Encountered an error while adding new application {request.json['appname']} to monitoring table")
        return f"Encountered an error while adding new application {request.json['appname']} to monitoring table \n"
    except Exception as e:
        app.logger.error(e)

@app.route("/list-item/<string:application>", methods=['GET'])
def list_item(application):
    try:
        reply = list_query(application)
        return {"ID": f"{reply[0]}", "appname": f"{reply[1]}", "status": f"{reply[2]}"}
    except Exception as e:
        app.logger.error(e)

@app.route("/list-items", methods=['GET'])
def list_items():
    try:
        reply = list_query(appname=None)
        ret = []
        for i in reply:
            ret.append({"ID": f"{i[0]}", "appname": f"{i[1]}", "status": f"{i[2]}"})
        return ret
    except Exception as e:
        app.logger.error(e)

@app.route("/get-status/<string:application>", methods=['GET'])
def get_item_status(application):
    try:
        return {"status": f"{get_status_query(appname=application)}"}
    except Exception as e:
        app.logger.error(e)

@app.route("/update-status", methods=['POST'])
def update_item_status():
    try:
        application = request.json["alerts"][0]["labels"]["appname"]
        if request.json["status"] == "resolved":
            new_status = "ok"
        else:
            new_status = "problem"
        app.logger.info(f"Received status update for app {application}, changing status to {new_status}")
        if update_status_query(appname=application,status=new_status):
            app.logger.info(f"Successfully changed status to {new_status} for app {application}")
            return {"status": "success"}, 200
        app.logger.error(f"Failed to change status to {new_status} for app {application}")
        return {"status": "failed"}, 200
    except Exception as e:
        app.logger.error(e)

def insert_query(appname):
    try:
        cur = conn.cursor()
        cur.execute(f"INSERT INTO monitoring(appname, status) VALUES ('{appname}', 'OK');")
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        app.logger.error("Encountered an error while inserting the new item: ")
        app.logger.error(e)
        conn.close()
        return False
    
def list_query(appname=None):
    try:
        cur = conn.cursor()
        if appname != None:
            cur.execute(f"SELECT * FROM monitoring WHERE appname = '{appname}';")
            ret = tuple(cur.fetchone())
        else:
            cur.execute(f"SELECT * FROM monitoring;")
            ret = list(cur.fetchall())
        return ret
    except Exception as e:
        app.logger.error("Encountered an error while performing the select query!")
        app.logger.error(e)
        conn.close()
        return "Encountered a problem while performing the select query!"
    
def get_status_query(appname):
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT status FROM monitoring WHERE appname = '{appname}';")
        status = cur.fetchone()[0]
        cur.close()
        return status
    except Exception as e:
        app.logger.error("Encountered an error while performing the select query!")
        app.logger.error(e)
        conn.close()
        return "Encountered a problem while performing the select query!"
    

def update_status_query(appname, status):
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE monitoring SET status = '{status}' WHERE appname = '{appname}';")
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.close()
        app.logger.error(e)
        return False
    


serve(app, host='0.0.0.0', port=8080)