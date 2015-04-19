 # -*- coding: utf-8 -*-
 
from __future__ import unicode_literals
from StringIO import StringIO
import time
import csv

from flask import render_template
from xhtml2pdf import pisa

import models

def make_pdf_from_applications(applications):
    html = render_template('applications_pdf.html',
        generation_date=time.strftime('%Y-%m-%d %H:%M'),
        applications=applications)

    f = StringIO()
    pisa.showLogging()
    pisa.CreatePDF(html, dest=f)

    return f.getvalue()

def make_csv_from_applications(applications):
    f = StringIO()
    writer = csv.writer(f)

    submitter_fields = ['name', 'email', 'phone_number', 'parent_name', 'parent_phone_number', \
        'parent_email', 'entering_grade', 'is_first_year_at_wshs']
    fields = submitter_fields + ['approved_courses', 'rejected_courses']

    # Header
    writer.writerow(fields)

    # TODO/HACK: Have users just enter first/last name in future
    for app in applications:
        parts = app.submitter['name'].strip().split(' ')
        parts.insert(0, parts.pop() + ',')
        app.submitter['name'] = ' '.join(parts)
    applications.sort(key=lambda a: a.submitter.name.lower())

    # Entries
    for app in applications:
        row = [app.submitter[field] for field in submitter_fields]
        row.append(', '.join(sorted([course_app.course.name for course_app in app.course_applications \
            if course_app.status == 'approved'])))
        row.append(', '.join(sorted([course_app.course.name for course_app in app.course_applications \
            if course_app.status == 'rejected'])))

        writer.writerow(row)

    return f.getvalue()