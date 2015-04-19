from datetime import date

from flask.ext.mongoengine import MongoEngine
from flask.ext.security import Security, MongoEngineUserDatastore

from applyapp import app

db = MongoEngine(app)

from models import User, Role
user_datastore = MongoEngineUserDatastore(db, User, Role)
security = Security(app, user_datastore)

@app.context_processor
def add_variables():
    return {
        'current_year': date.today().year,
        'is_prod': app.config.get('IS_PRODUCTION'),
        'due_date': app.config.get('DUE_DATE')
    }
