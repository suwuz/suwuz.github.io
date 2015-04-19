import logging

from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask.ext.pagedown import PageDown
from flaskext.markdown import Markdown

import config

# Create app
app = Flask(__name__)
app.config.from_object(config)
Mail(app)
Bootstrap(app)
PageDown(app)
Markdown(app)

@app.before_first_request
def setup_logging():
    if not app.debug:
        # In production mode, add log handler to sys.stderr
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.INFO)

# Load views
import applyapp.views
