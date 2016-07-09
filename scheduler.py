import os, click, json, sqlite3
import datetime
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.base import ConflictingIdError
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, make_response
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import requests
import sendgrid

logging.basicConfig()
#import click
app = Flask(__name__)
# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'db', 'notifications.db'),
    SECRET_KEY='secret',
    USERNAME='admin',
    PASSWORD='default'
))

# scheduler
sched = BackgroundScheduler(timezone='America/Los_Angeles')
sched.add_jobstore('sqlalchemy', url='sqlite:///db/notifications.db')
sched.add_executor('threadpool')
sched.start()

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = dict_factory
    return rv

@app.cli.command('initdb')
@click.option('--file',help='the schema file')
def initdb_command(file):
    initdb(file)

def initdb(file):
    """Initialize the database."""
    print "initializing " + file
    db = get_db()
    with app.open_resource(file, mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route("/notifications/add", methods=['POST'])
def addNotification():
    if request.method != 'POST':
        return make_response("",405)
    if request.headers['Content-Type'] != 'application/json':
        return make_response("",415)
    payload = json.loads(request.data)
    if not validatePayload(payload):
        return make_response("",400)
    try:
        sched.add_job(send, 'date', run_date=datetime.datetime.strptime(payload['end_date'] + ' 10:00', '%Y-%m-%d %H:%M'), args=[payload], id=str(payload['reservation_id']))
    except apscheuler.ConflictingIdError:
        return make_response("reservation id %s already exists" % str(payload['reservation_id']))
    return make_response("",200)

def validatePayload(payload):
    if all (k in payload for k in ('reservation_id', 'end_date', 'first_name', 'last_name', 'email_address')):
        return True
    return False

@app.route("/notifications", methods=['GET','DELETE'])
def listNotifications():
    db = get_db()
    if request.method == 'GET':
        rows = []
        rows = db.execute('select id as reservation_id, next_run_time as reminder_time from apscheduler_jobs').fetchall()
        results = {"notifications": rows}
        return make_response(json.dumps(results), 200)
    if request.method == 'DELETE':
        reservation_id = request.form.get('reservation_id')
        if reservation_id is None:
            sched.remove_all_jobs()
            return make_response("",200)
        sched.remove_job(id=reservation_id)
        return make_response("",200)
    return make_response("",405)

def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def send(payload):
    headers = {"Authorization": "Bearer %s" % os.environ.get('SENDGRID_API_KEY'),
               "Content-Type": "application/json"}
    message = {
                  "from":{"name":"Linda Kim", "email":"linda.kim@gpmail.org"},
                  "content":[
                      {"type":"text/plain",
                      "value":"Hi, I hope you enjoyed your stay at SMC! This is a reminder to please send me a picture of the cleaning checklist. Thank you!"}],
                  "personalizations":[{"to":[{"email":payload['email_address']}]}],
                  "subject": "SMC Cleaning - Reminder"
        }
    url = "https://api.sendgrid.com/v3/mail/send"
    r = requests.post(url=url, headers=headers, data=json.dumps(message))

if __name__ == "__main__":
    app.run()
