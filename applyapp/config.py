import os

SECRET_KEY = os.environ['SECRET_KEY']
IS_PRODUCTION = int(os.environ.get('IS_PRODUCTION', False))

DUE_DATE = 'Friday, March 27, 2015 at 11:59pm'
APPS_ARE_CLOSED = True

ADMIN_USER = os.environ['ADMIN_USER']
ADMIN_PASSWORD = os.environ['ADMIN_PASSWORD']

MONGODB_SETTINGS = {
    'db': os.environ.get('MONGODB_DATABASE', os.environ.get('DB_NAME')),
    'host': os.environ.get('MONGO_URL', os.environ.get('DB_HOST'))
}

SECURITY_POST_LOGOUT_VIEW = '/login'
SECURITY_PASSWORD_HASH = 'pbkdf2_sha512'
SECURITY_PASSWORD_SALT = os.environ['SALT']
SECURITY_REGISTERABLE = True
SECURITY_RECOVERABLE = True

MAIL_DEFAULT_SENDER = SECURITY_EMAIL_SENDER = ('WSHS AP Applications', 'no-reply@scsk12.org')
SECURITY_SEND_REGISTER_EMAIL = False

# Flask-Mail configuration
MAIL_SERVER = '96.4.164.31'
MAIL_PORT = 25
