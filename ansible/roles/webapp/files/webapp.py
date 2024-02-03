from flask import Flask

from flask import request

from waitress import serve

import psycopg2

import json

import os

from logging.config import dictConfig

# Configure logging settings for the webapp
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
# Create Flask object that will be used for providing webapp services
app = Flask(__name__)

# Load database user and password from Docker secrets
with open('/run/secrets/pg-user') as userfile:
    dbuser = userfile.readline().strip()
with open('/run/secrets/pg-secret') as passfile:
    dbpass = passfile.readline().strip()

# Configure the PostgreSQL connection for the webapp
conn = psycopg2.connect(
        host=os.environ.get('DBHOST'),
        database=os.environ.get('DB'),
        user=dbuser,
        password=dbpass
        )

@app.route("/")
def info():
    """
    Function that returns a greeting if the webapp is up and running.
    """
    return "Hello there! Demo web app is alive! \n"


@app.route("/insert-item", methods=['POST'])
def insert_item():
    """
    Function that adds a new application to the monitoring table based on the received POST request. Check the documentation for exact details about the expected body of the POST request.
    """
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
    """
    Function that returns all details about the specified application if it exists in the monitoring table.
    """
    try:
        reply = list_query(application)
        return {"ID": f"{reply[0]}", "appname": f"{reply[1]}", "status": f"{reply[2]}"}
    except Exception as e:
        app.logger.error(e)

@app.route("/list-items", methods=['GET'])
def list_items():
    """
    Function that return all details about every application that exists in the monitoring table.
    """
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
    """
    Function that returns the status of the specified application if it exists in the monitoring table.
    """
    try:
        return {"status": f"{get_status_query(appname=application)}"}
    except Exception as e:
        app.logger.error(e)

@app.route("/update-status", methods=['POST'])
def update_item_status():
    """
    Function that updates the status of specific application based on the body of the received request. Check the webapp documentation for exact details about the expected body of the POST request.
    """
    try:
        application = request.json["alerts"][0]["labels"]["appname"]
        if request.json["status"] == "resolved":
            new_status = "OK"
        else:
            new_status = "PROBLEM"
        app.logger.info(f"Received status update for app {application}, changing status to {new_status}")
        if update_status_query(appname=application,status=new_status):
            app.logger.info(f"Successfully changed status to {new_status} for app {application}")
            return {"status": "success"}, 200
        app.logger.error(f"Failed to change status to {new_status} for app {application}")
        return {"status": "failed"}, 200
    except Exception as e:
        app.logger.error(e)

def insert_query(appname):
    """
    Function that performs the SQL INSERT query that adds a new application to the monitoring table.
    """
    cur = conn.cursor()
    try:
        cur.execute(f"INSERT INTO monitoring(appname, status) VALUES ('{appname}', 'OK');")
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        app.logger.error("Encountered an error while inserting the new item: ")
        app.logger.error(e)
        conn.rollback()
        cur.close()
        return False
    
def list_query(appname=None):
    """
    Function that performs the SQL SELECT query for listing all details about the specified application or all of the applications in the table.
    """
    cur = conn.cursor()
    try:
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
        cur.close()
        return "Encountered a problem while performing the select query!"
    
def get_status_query(appname):
    """
    Function that performs the SQL SELECT query for obtaining status of the specified application.
    """
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT status FROM monitoring WHERE appname = '{appname}';")
        status = cur.fetchone()[0]
        cur.close()
        return status
    except Exception as e:
        app.logger.error("Encountered an error while performing the select query!")
        app.logger.error(e)
        cur.close()
        return "Encountered a problem while performing the select query!"
    

def update_status_query(appname, status):
    """
    Function that performs the SQL UPDATE query for updating the status of specified application.
    """
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE monitoring SET status = '{status}' WHERE appname = '{appname}';")
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        app.logger.error(e)
        conn.rollback()
        cur.close()
        return False
    

# Start up the flask app with waitress
serve(app, host='0.0.0.0', port=8080)