from flask.ext.security import current_user, url_for_security, utils as security_utils

from applyapp import app
from core import user_datastore

@app.before_first_request
def initial_setup():
    """Sets up roles and creates an initial account to use
    for authentication.
    """

    # Set up roles
    for r in (('admin', 'Admin'),
              ('reviewer', 'Application reviewer'),
              ('student', 'Student')):
        user_datastore.find_or_create_role(name=r[0], description=r[1])

    # Create default user
    email = app.config.get('ADMIN_USER')
    password = app.config.get('ADMIN_PASSWORD')
    roles = ['admin', 'reviewer']

    existing = user_datastore.find_user(email=email)
    if existing:
        user_datastore.delete_user(existing)

    user = user_datastore.create_user(
        email=email,
        password=security_utils.encrypt_password(password)
    )

    for role in roles:
        user_datastore.add_role_to_user(user, role)

def login(user):
    return security_utils.login_user(user)