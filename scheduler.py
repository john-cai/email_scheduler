import os, click, json, sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, make_response
#import click
app = Flask(__name__)
# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'db', 'notifications.db'),
    SECRET_KEY='secret',
    USERNAME='admin',
    PASSWORD='default'
))

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
    db = get_db()

    db.execute('insert into notifications (reservation_id, end_date, first_name, last_name, email_address) values(?,?,?,?,?)',
               [payload['reservation_id'], payload['end_date'], payload['first_name'], payload['last_name'], payload['email_address']])
    db.commit()
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
        rows = db.execute('select reservation_id, first_name, last_name, email_address, end_date from notifications').fetchall()
        print str(rows)
        results = {"notifications": rows}
        return make_response(json.dumps(results), 200)
    if request.method == 'DELETE':
        reservation_id = request.form.get('reservation_id')
        if reservation_id is None:
            return make_response("missing valid reservation_id", 400)
        db.execute("delete from notifications where reservation_id = ?",[reservation_id])
        db.commit()
        return make_response("",200)
    return make_response("",405)

def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

if __name__ == "__main__":
    app.run()
