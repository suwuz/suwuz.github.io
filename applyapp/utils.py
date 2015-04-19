import json
import base64
from collections import OrderedDict

from flask import current_app, render_template
from flask.ext.security import current_user
from flask_mail import Message

import gridfs
from bson.objectid import ObjectId
from mongoengine.connection import get_db, DEFAULT_CONNECTION_NAME

import models

fs = gridfs.GridFS(get_db(DEFAULT_CONNECTION_NAME), 'fs')

def get_file_from_db(file_id):
    return fs.get(ObjectId(file_id))

def get_teacher_for_hash(hashed):
    return models.Teacher.objects.with_id(base64.b64decode(hashed).replace(current_app.config['SECRET_KEY'], ''))

def get_hash_for_teacher(teacher):
    return base64.b64encode(current_app.config['SECRET_KEY'] + str(teacher.id))

def serialize_application_to_html(application, is_review=False):
    return render_template('_formatted_application.html',
        application=application,
        submitter=application.submitter,
        course_apps=application.course_applications,
        teacher_recs=application.teacher_recs,
        test_scores=application.test_scores,
        current_ap_courses=application.current_ap_courses,
        is_reviewer=current_user.has_role('reviewer'),
        is_review=is_review)

def serialize_application_to_json(application):
    submitter = OrderedDict(sorted(json.loads(application.submitter.to_json()).items(), key=lambda t: t[0]))
    del submitter['active'], submitter['_id'], submitter['password'], submitter['roles']

    general = {
        'test_scores': application.test_scores or 'None',
        'current_ap_courses': application.current_ap_courses or 'None',
        'recommending_teachers': [rec.teacher.name for rec in application.teacher_recs] or 'None',
        'desired_courses': [app.course.name for app in application.course_applications]
    }

    courses = [OrderedDict(
            [
                ('name', course_app.course.name),
                ('average_okay', course_app.average_okay),
                ('have_met_reqs', course_app.have_met_reqs)
            ] + ([
                ('uploaded_files', [f.name for f in course_app.uploaded_content] or 'None')
            ] if course_app.course.upload_required else [])
        ) for course_app in application.course_applications]

    return json.dumps(OrderedDict((
        ('submitter', submitter),
        ('general', general),
        ('courses', courses)
    )), indent=4)

def send_email(subject, recipient, template_name, **context):
    if not current_app.config['IS_PRODUCTION']:
        print 'Not sending--in development.'
        print render_template('email/%s.html' % template_name, **context)
        return

    print 'Sending email to %s' % recipient

    msg = Message(subject, recipients=[recipient])

    msg.html = render_template('email/%s.html' % template_name, **context)

    mail = current_app.extensions.get('mail')
    mail.send(msg)

def send_application_submit_email(application):
    send_email('Your WSHS AP Application has been submitted successfully!',
        recipient=application.submitter.email,
        template_name='application_submitted',
        application=application,
        raw_application=serialize_application_to_json(application)
    )

def send_application_creation_email(application):
    send_email('Your WSHS AP Application has been created!',
        recipient=application.submitter.email,
        template_name='application_created',
        application=application
    )
