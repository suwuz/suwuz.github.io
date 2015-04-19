import json
import datetime
import csv
import zipfile
from StringIO import StringIO

import mongoengine
from werkzeug import secure_filename
from flask import request, render_template, redirect, url_for, flash, current_app, make_response
from flask.ext.security import roles_required, login_required, current_user, registerable

from core import app, user_datastore
import auth, forms, models, utils, exporter

@app.route('/')
def home():
    if current_user.is_authenticated():
        return redirect('dashboard')
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.has_role('reviewer'):
        return reviewer_dashboard()
    else:
        return student_dashboard()

def student_dashboard():
    applications = models.Application.objects(submitter=current_user.id)
    return render_template('dashboard_student.html',
        applications=applications)

def reviewer_dashboard():
    recommendations_ct = 0
    completed_rec_ct = 0
    course_app_ct = 0

    for app in models.Application.objects:
        recommendations_ct += len(app.teacher_recs)
        completed_rec_ct += len([rec for rec in app.teacher_recs if rec.status != 'pending'])
        course_app_ct += len(app.course_applications)

    return render_template('dashboard_reviewer.html',
        courses=len(models.Course.objects),
        applications=len(models.Application.objects),
        users=len(models.User.objects),
        recommendations=recommendations_ct,
        completed_rec_ct=completed_rec_ct,
        course_app_ct=course_app_ct
    )

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    return edit_user(current_user.id)

@app.route('/users')
@login_required
@roles_required('reviewer')
def users():
    users = models.User.objects()
    return render_template('users.html', users=users)

@app.route('/users/<user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    is_reviewer = current_user.has_role('reviewer')
    user = user_datastore.get_user(user_id)

    if (not current_user.is_authenticated()) or (user.id != current_user.id and not is_reviewer):
        return current_app.login_manager.unauthorized()

    form = forms.UserEditForm(request.form, user)
    form.roles.choices = [(role.name, role.name.capitalize()) for role in user_datastore.role_model.objects()]

    if not current_user.has_role('admin'):
        del form.roles

    if form.validate_on_submit():
        user.email = form.email.data
        if form.password.data:
            user.password = form.password.data
        if current_user.has_role('admin'):
            user.roles = [user_datastore.find_role(role) for role in form.roles.data]

        user.save()
        flash('User updated successfully.', 'success')

    if current_user.has_role('admin'):
        form.roles.data = [role.name for role in user.roles]

    return render_template('edit_user.html', form=form)

@app.route('/users/new', methods=['GET', 'POST'])
@login_required
@roles_required('reviewer')
def add_user():
    form = forms.UserEditForm(request.form)
    form.roles.choices = [(role.name, role.name.capitalize()) for role in user_datastore.role_model.objects()]

    if form.validate_on_submit():
        user = models.User(
            email=form.email.data,
            password=form.password.data
        )

        for role in form.roles.data:
            user_datastore.add_role_to_user(user, role)

        user.save()
        flash('User created successfully.', 'success')
        return redirect(url_for('users'))

    return render_template('edit_user.html', form=form, is_new=True)

@app.route('/users/<user_id>/delete')
@login_required
@roles_required('reviewer')
def delete_user(user_id):
    user = user_datastore.get_user(user_id)

    if user == current_user:
        flash('You cannot delete yourself!', 'error')
        return redirect(request.args['next'])

    user.delete()
    flash('User deleted successfully.', 'success')
    return redirect(request.args['next'])

@app.route('/courses')
@login_required
@roles_required('reviewer')
def courses():
    course_app_map = {}
    for application in models.Application.objects:
        for course_app in application.course_applications:
            if course_app.course in course_app_map:
                course_app_map[course_app.course].append((application, course_app))
            else:
                course_app_map[course_app.course] = [(application, course_app)]

    courses = models.Course.objects.order_by('name')
    for course in courses:
        course.associated_apps = course_app_map.get(course)

    return render_template('courses.html', courses=courses)

@app.route('/courses/new', methods=['GET', 'POST'])
@login_required
@roles_required('reviewer')
def add_course():
    form = forms.CourseEditForm()
    if form.validate_on_submit():
        course = models.Course(
            name=form.name.data,
            description=form.description.data,
            requirements=form.requirements.data,
            upload_required=form.upload_required.data,
            open_for_applications=form.open_for_applications.data
        )
        course.save()
        flash('Course created successfully.', 'success')
        return redirect('courses')
    return render_template('edit_course.html', form=form, is_new=True)

@app.route('/courses/<course_id>')
def view_course(course_id):
    course = models.Course.objects.with_id(course_id)
    return render_template('view_course.html', course=course)

@app.route('/courses/<course_id>/applications', methods=['GET'])
@login_required
@roles_required('reviewer')
def view_course_applications(course_id):
    course = models.Course.objects.with_id(course_id)
    applications = []

    for application in models.Application.objects:
        for course_app in application.course_applications:
            if course_app.course == course:
                applications.append((application, course_app))

    return render_template('course_applications.html',
        course=course,
        applications=applications
    )

@app.route('/courses/<course_id>/applications/download_samples', methods=['GET'])
@login_required
@roles_required('reviewer')
def download_combined_uploaded_files(course_id):
    course = models.Course.objects.with_id(course_id)
    dir_name = course.name
    files = []

    for application in models.Application.objects:
        for course_app in application.course_applications:
            if course_app.course == course:
                for f in course_app.uploaded_content:
                    files.append(f)

    output = StringIO()

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for application in models.Application.objects:
            for course_app in application.course_applications:
                if course_app.course == course:
                    total = len(course_app.uploaded_content)
                    for i, f in enumerate(course_app.uploaded_content):
                        name = dir_name + '/' + application.submitter.name.replace(' ', '')
                        if total > 1:
                            name += '-' + str(i)
                        name += '.docx'
                        archive.writestr(name, f.read())

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename={}.zip'.format(dir_name)
    return response

@app.route('/courses/<course_id>/applications/review_uploaded_files', methods=['GET'])
@login_required
@roles_required('reviewer')
def review_uploaded_files(course_id):
    course = models.Course.objects.with_id(course_id)
    applications = []

    for application in models.Application.objects:
        for course_app in application.course_applications:
            if course_app.course == course:
                applications.append((application, course_app))

    return render_template('review_uploaded_files.html',
        course=course,
        applications=applications
    )

@app.route('/courses/_review/<application_id>/<course_id>', methods=['GET', 'POST'])
def submit_review(application_id, course_id):
    application = models.Application.objects.with_id(application_id)
    course = models.Course.objects.with_id(course_id)

    relevant_course_app = None
    for course_app in application.course_applications:
        if course_app.course == course:
            relevant_course_app = course_app
            continue

    relevant_course_app.writing_sample_status = request.args['status']
    application.save()
    return render_template('_uploaded_file_table_item.html',
        status=relevant_course_app.writing_sample_status,
        application=application,
        course_app=relevant_course_app
    )

@app.route('/courses/<course_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('reviewer')
def edit_course(course_id):
    course = models.Course.objects.with_id(course_id)
    form = forms.CourseEditForm(request.form, course)
    if form.validate_on_submit():        
        form.populate_obj(course)
        course.save()
        flash('Course updated successfully.', 'success')
        return redirect('courses')
    return render_template('edit_course.html', form=form)

@app.route('/courses/<course_id>/close')
@login_required
@roles_required('reviewer')
def close_course(course_id):
    course = models.Course.objects.with_id(course_id)
    course.open_for_applications = False
    course.save()
    flash('Course closed successfully.', 'success')
    return redirect(request.args['next'])

@app.route('/courses/<course_id>/open')
@login_required
@roles_required('reviewer')
def open_course(course_id):
    course = models.Course.objects.with_id(course_id)
    course.open_for_applications = True
    course.save()
    flash('Course opened successfully.', 'success')
    return redirect(request.args['next'])

@app.route('/courses/<course_id>/delete')
@login_required
@roles_required('reviewer')
def delete_course(course_id):
    course = models.Course.objects.with_id(course_id)
    course.delete()
    flash('Course deleted successfully.', 'success')
    return redirect(request.args['next'])

@app.route('/teachers')
@login_required
@roles_required('reviewer')
def teachers():
    teachers = models.Teacher.objects()

    for teacher in teachers:
        teacher.hash = utils.get_hash_for_teacher(teacher)

    return render_template('teachers.html', teachers=teachers)

@app.route('/teachers/new', methods=['GET', 'POST'])
@login_required
@roles_required('reviewer')
def add_teacher():
    form = forms.TeacherEditForm()
    if form.validate_on_submit():
        teacher = models.Teacher(
            name=form.name.data,
            email=form.email.data,
            is_pseudo=form.is_pseudo.data
        )
        teacher.save()
        flash('Teacher created successfully.', 'success')
        return redirect('teachers')
    return render_template('edit_teacher.html', form=form, is_new=True)

@app.route('/teachers/new/bulk', methods=['GET', 'POST'])
@login_required
@roles_required('reviewer')
def add_teacher_bulk():
    form = forms.TeacherAddBulkForm()
    if form.validate_on_submit():
        skipped = 0
        added = 0

        reader = csv.reader(form.raw.data.split('\n'))
        for row in reader:
            if models.Teacher.objects(name=row[1]):
                skipped += 1
                continue

            teacher = models.Teacher(
                name=row[0],
                email=row[1]
            )
            teacher.save()
            added += 1

        flash( str(added) + ' teachers created successfully (skipped ' + str(skipped) + ').', 'success')
        return redirect('teachers')

    return render_template('add_teacher_bulk.html', form=form)

@app.route('/teachers/<teacher_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('reviewer')
def edit_teacher(teacher_id):
    teacher = models.Teacher.objects.with_id(teacher_id)
    form = forms.TeacherEditForm(request.form, teacher)
    if form.validate_on_submit():        
        form.populate_obj(teacher)
        teacher.save()
        flash('Teacher updated successfully.', 'success')
        return redirect('teachers')
    return render_template('edit_teacher.html', form=form)

@app.route('/teachers/<teacher_id>/delete')
@login_required
@roles_required('reviewer')
def delete_teacher(teacher_id):
    teacher = models.Teacher.objects.with_id(teacher_id)
    teacher.delete()
    flash('Teacher deleted successfully.', 'success')
    return redirect(request.args['next'])

@app.route('/download')
def download_file():
    grid_file = utils.get_file_from_db(request.args.get('file'))
    response = make_response(grid_file.read())
    response.headers['Content-Disposition'] = 'attachment; filename={}'.format(grid_file.name)
    return response

@app.route('/applications')
@roles_required('reviewer')
def applications():
    """View submitted applications."""
    applications = models.Application.objects()
    return render_template('applications.html', applications=applications)

@app.route('/applications/download_pdf')
@roles_required('reviewer')
def download_applications():
    applications = models.Application.objects()
    applications = sorted(applications, key=lambda a: a.submitter.name.lower())
    response = make_response(exporter.make_pdf_from_applications(applications))
    response.headers['Content-Disposition'] = 'attachment; filename=ExportedApplications.pdf'
    return response

@app.route('/applications/download_csv')
@roles_required('reviewer')
def download_applications_csv():
    applications = models.Application.objects()
    applications = sorted(applications, key=lambda a: a.submitter.name.lower())
    response = make_response(exporter.make_csv_from_applications(applications))
    response.headers['Content-Disposition'] = 'attachment; filename=ExportedApplications.csv'
    return response

@app.route('/applications/new', methods=['GET', 'POST'])
def new_application():
    """Begin a new application."""

    if current_user.is_authenticated():
        existing = models.Application.objects(submitter=current_user.id).first()
        if existing:
            return redirect(url_for('application', application_id=existing.id, step=1))
        else:
            new_app = models.Application(submitter=current_user.id)
            new_app.save()
            utils.send_application_creation_email(new_app)
            return redirect(url_for('application', application_id=new_app.id, step=1))

    form = forms.ApplicationFormStep_New()
    if form.validate_on_submit():
        if user_datastore.get_user(form.email.data):
            flash('A user with that email address already exists. Perhaps you meant to log in instead?', 'error')
            return redirect(url_for('new_application'))
        else:
            registerable.register_user(
                name=form.name.data,
                email=form.email.data,
                password=form.password.data,
                roles=['student']
            )

            user = user_datastore.get_user(form.email.data)
            application = models.Application(submitter=user.id)
            application.save()
            utils.send_application_creation_email(application)

            auth.login(user)
            flash(('A new account has been created with the email address <b>' + user.email + '</b>. You don\'t need to complete your application '
                'in one sitting; return later and log back in to continue right where you left off.'), 'success')
            return redirect(url_for('application', application_id=application.id, step=2))

    return render_template('application_new.html', form=form)

@app.route('/applications/<application_id>/view')
def view_application(application_id, is_review=False):
    is_reviewer = current_user.has_role('reviewer')
    application = models.Application.objects.with_id(application_id)

    if not application:
        flash('No application with that id could be found.', 'error')
        return redirect('dashboard')

    if (not current_user.is_authenticated()) or (application.submitter.id != current_user.id and not is_reviewer):
        return current_app.login_manager.unauthorized()

    date = (application.submit_date if application.is_submitted else application.id.generation_time)

    files = []
    for course_app in application.course_applications:
        if course_app.uploaded_content:
            for f in course_app.uploaded_content:
                files.append({'name': f.name, 'url': url_for('download_file', file=f._id)})

    return render_template('view_application.html',
        name=application.submitter.name,
        date=date.strftime('%Y-%m-%d') if date else 'No date available',
        files=files,
        formatted=utils.serialize_application_to_html(application, is_review=is_review)
    )

@app.route('/applications/<application_id>', methods=['GET', 'POST'])
@app.route('/applications/<application_id>/<int:step>', methods=['GET', 'POST'])
@app.route('/applications/<application_id>/<int:step>/<int:course_index>', methods=['GET', 'POST'])
@login_required
def application(application_id, step=None, course_index=None):
    """View an application details."""

    is_reviewer = current_user.has_role('reviewer')
    application = models.Application.objects.with_id(application_id)

    if not application:
        flash('No application with that id could be found.', 'error')
        return redirect('dashboard')

    if (not current_user.is_authenticated()) or (application.submitter.id != current_user.id and not is_reviewer):
        return current_app.login_manager.unauthorized()

    if not is_reviewer and application.is_submitted:
        return redirect('view_application', application_id=application_id)

    if not step:
        return redirect(url_for('application', application_id=application_id, step=1))

    if step == 1:
        form = forms.ApplicationFormStep_New(request.form, application.submitter)
        del form.email, form.password, form.confirm_password

        if form.validate_on_submit():
            application.submitter.name = form.name.data
            application.submitter.save()
            flash('Student information saved successfully.', 'success')
            return redirect(url_for('application', application_id=application.id, step=2))

        return render_template('application_new.html', form=form, is_existing=True)

    if step == 2:
        form = forms.ApplicationFormStep_UserDetail(request.form, application.submitter)

        if form.validate_on_submit():
            application.submitter.phone_number = form.phone_number.data
            application.submitter.parent_name = form.parent_name.data
            application.submitter.parent_phone_number = form.parent_phone_number.data
            application.submitter.parent_email = form.parent_email.data
            application.submitter.entering_grade = form.entering_grade.data
            application.submitter.is_first_year_at_wshs = form.is_first_year_at_wshs.data
            application.submitter.save()

            application.taking_ap_courses = form.taking_ap_courses.data
            application.current_ap_courses = form.current_ap_courses.data if form.taking_ap_courses.data else ''
            application.test_scores = form.test_scores.data
            application.save()

            flash('Student information saved successfully.', 'success')
            if form.prev.data:
                return redirect(url_for('application', application_id=application_id, step=1))
            elif form.save.data:
                return redirect(request.path)
            else:
                return redirect(url_for('application', application_id=application.id, step=3))

        form.entering_grade.data = application.submitter.entering_grade or 0
        form.taking_ap_courses.data = application.taking_ap_courses
        form.current_ap_courses.data = application.current_ap_courses
        form.test_scores.data = application.test_scores

        return render_template('application_userdetail.html', form=form)

    if step == 3:
        form = forms.ApplicationFormStep_Courses(request.form, data={
            'desired_courses': [app.course.id for app in application.course_applications]
        })

        form.desired_courses.choices = [(course.id, course.name) for course in models.Course.objects(open_for_applications=True).order_by('name')]

        if form.validate_on_submit():
            for course in models.Course.objects():
                course_apps = [a for a in application.course_applications if a.course == course]
                if not course_apps and course.id in form.desired_courses.data:
                    application.course_applications.append(models.CourseApplication(course=course))
                elif course_apps and course.id not in form.desired_courses.data:
                    application.course_applications.remove(course_apps[0])

            application.save()
            flash('Course information saved successfully.', 'success')
            if form.prev.data:
                return redirect(url_for('application', application_id=application_id, step=2))
            elif form.save.data:
                return redirect(request.path)
            else:
                return redirect(url_for('application', application_id=application_id, step=4))

        return render_template('application_wants.html', form=form)

    if step == 4:
        if course_index == None:
            return redirect(url_for('application', application_id=application_id, step=4, course_index=0))

        if course_index > application.course_applications.count() - 1:
            return redirect(url_for('application', application_id=application_id, step=5))

        course_app = application.course_applications[course_index]
        form = forms.ApplicationFormStep_Course(request.form, data={
            'average_okay': course_app.average_okay,
            'have_met_reqs': course_app.have_met_reqs
        })

        # Dropzone.js special case
        if request.method == 'POST' and len(request.files):
            for _, f in request.files.iteritems():
                proxy = mongoengine.fields.GridFSProxy()
                proxy.put(f, content_type=f.content_type, filename=secure_filename(f.filename))
                course_app.uploaded_content.append(proxy)
            application.save()
            application.reload()
            application.save()
            return 'File uploaded successfully!'

        if form.validate_on_submit():
            course_app.average_okay = form.average_okay.data
            course_app.have_met_reqs = form.have_met_reqs.data

            application.save()
            flash('"' + course_app.course.name + '" information saved successfully.', 'success')

            if form.save.data:
                return redirect(request.path)
            elif form.prev.data and course_index > 0:
                return redirect(url_for('application', application_id=application_id, step=4, course_index=course_index - 1))
            elif form.prev.data and course_index == 0:
                return redirect(url_for('application', application_id=application_id, step=3))
            elif course_index < application.course_applications.count() - 1:
                return redirect(url_for('application', application_id=application_id, step=4, course_index=course_index + 1))
            else:
                return redirect(url_for('application', application_id=application_id, step=5))

        return render_template('application_course.html',
            name=course_app.course.name,
            course=course_app.course,
            form=form,
            prev_uploads=json.dumps([{ 'name': f.name, 'size': f.get().length } for f in course_app.uploaded_content]))

    if step == 5:
        if application.submitter.is_first_year_at_wshs:
            form = forms.ApplicationFormStep_FirstYear(request.form, data={
                'understand': len(application.teacher_recs) > 0
            })

            if form.validate_on_submit():
                if form.understand.data:
                    application.teacher_recs = []
                    application.teacher_recs.append(models.TeacherRec(teacher=models.Teacher.objects.get_or_create(name='First year student - will bring to school', is_pseudo=True)[0]))
                elif not form.understand.data and len(application.teacher_recs) > 0:
                    application.teacher_recs = []

                application.save()
                flash('Teacher recommendations saved successfully.', 'success')

                if form.prev.data:
                    return redirect(url_for('application', application_id=application_id, step=4 if application.course_applications.count() > 0 else 3))
                elif form.save.data:
                    return redirect(request.path)
                else:
                    return redirect(url_for('application', application_id=application_id, step=6))

            return render_template('application_recs.html', form=form, is_first_year_at_wshs=True)

        form = forms.ApplicationFormStep_Recs(request.form, data={
            'teacher_recs': [rec.teacher.id for rec in application.teacher_recs]
        })

        form.teacher_recs.choices = [(teacher.id, teacher.name) for teacher in models.Teacher.objects(is_pseudo__ne=True)]

        if form.validate_on_submit():
            application.confirm_contacted_teachers = form.confirm_contacted.data

            for teacher in models.Teacher.objects():
                recs = [r for r in application.teacher_recs if r.teacher == teacher]
                if not recs and teacher.id in form.teacher_recs.data:
                    application.teacher_recs.append(models.TeacherRec(teacher=teacher))
                elif recs and teacher.id not in form.teacher_recs.data:
                    application.teacher_recs.remove(recs[0])

            application.save()
            flash('Teacher recommendations saved successfully.', 'success')
            if form.prev.data:
                return redirect(url_for('application', application_id=application_id, step=4 if application.course_applications.count() > 0 else 3))
            elif form.save.data:
                return redirect(request.path)
            else:
                return redirect(url_for('application', application_id=application_id, step=6))

        return render_template('application_recs.html', form=form)        

    if step == 6:
        form = forms.ApplicationFormStep_Final()

        if form.validate_on_submit():
            if form.prev.data:
                return redirect(url_for('application', application_id=application_id, step=5))
            elif form.save.data:
                return redirect(url_for('dashboard'))

            application.is_submitted = True
            application.submit_date = datetime.datetime.now()
            application.save()
            flash('Your application has been submitted successfully.', 'success')

            # Send email confirmation
            utils.send_application_submit_email(application)

            return redirect(url_for('dashboard'))

        return render_template('application_final.html', form=form,
            recap=utils.serialize_application_to_html(application))

    flash('Application could not be opened.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/applications/<application_id>/<int:step>/<int:course_index>/delete_file')
@login_required
def delete_file(application_id, step, course_index):
    is_reviewer = current_user.has_role('reviewer')
    application = models.Application.objects.with_id(application_id)

    if (not current_user.is_authenticated()) or (application.submitter.id != current_user.id and not is_reviewer):
        return current_app.login_manager.unauthorized()

    name = request.args.get('name')
    course_app = application.course_applications[course_index]
    for f in course_app.uploaded_content:
        if f.name == name:
            f.delete()
            course_app.uploaded_content.remove(f)
    application.save()
    return 'File deleted successfully!'

@app.route('/applications/<application_id>/delete')
@login_required
def delete_application(application_id):
    is_reviewer = current_user.has_role('reviewer')
    application = models.Application.objects.with_id(application_id)

    if (not current_user.is_authenticated()) or (application.submitter.id != current_user.id and not is_reviewer):
        return current_app.login_manager.unauthorized()

    application.delete()
    flash('Application deleted successfully.', 'success')
    return redirect(request.args['next'])

@app.route('/applications/review')
@login_required
@roles_required('reviewer')
def review_applications():
    applications = models.Application.objects()
    return render_template('review_applications.html', applications=applications)

@app.route('/applications/review/<application_id>')
@login_required
@roles_required('reviewer')
def review_application(application_id):
    return view_application(application_id, is_review=True)

@app.route('/applications/review/email', methods=['GET', 'POST'])
@login_required
@roles_required('reviewer')
def email_application_results():
    if request.method == 'POST':
        if request.form.get('id'):
            application = models.Application.objects.with_id(request.form['id'])
            approved_apps = [app for app in application.course_applications if app.status == 'approved']
            utils.send_email('Your AP application has been reviewed',
                recipient=application.submitter.email,
                template_name='application_reviewed',
                application=application,
                approved_apps=approved_apps
            )
            flash('Review email has been sent successfully.', 'success')
            return redirect(url_for('email_application_results'))

        else:
            for application in models.Application.objects():
                approved_apps = [app for app in application.course_applications if app.status == 'approved']
                utils.send_email('Your AP application has been reviewed',
                    recipient=application.submitter.email,
                    template_name='application_reviewed',
                    application=application,
                    approved_apps=approved_apps
                )

            flash('Review emails have been sent successfully.', 'success')
            return redirect(url_for('email_application_results'))
    else:
        applications = models.Application.objects()

        # Add counts
        for app in applications:
            app.approved_ct = 0
            app.rejected_ct = 0
            app.pending_ct = 0
            for course_app in app.course_applications:
                if course_app.status == 'approved':
                    app.approved_ct += 1
                elif course_app.status == 'rejected':
                    app.rejected_ct += 1
                elif course_app.status == 'pending':
                    app.pending_ct += 1

        return render_template('email_application_results.html',
            applications=applications
        )


    return render_template('review_applications.html', applications=applications)

@app.route('/applications/review/<application_id>/<course_id>', methods=['GET', 'POST'])
def submit_application_review(application_id, course_id):
    application = models.Application.objects.with_id(application_id)
    course = models.Course.objects.with_id(course_id)

    relevant_course_app = None
    for course_app in application.course_applications:
        if course_app.course == course:
            relevant_course_app = course_app
            continue

    relevant_course_app.status = request.args['status']
    application.save()
    return render_template('_review_app_item.html',
        status=relevant_course_app.status,
        application=application,
        course_app=relevant_course_app
    )

@app.route('/recommendations', methods=['GET', 'POST'])
@login_required
@roles_required('reviewer')
def recommendations():
    teachers = {}

    for app in models.Application.objects.order_by('submitter.name'):
        for rec in app.teacher_recs:
            if rec.teacher in teachers:
                teachers[rec.teacher].append(rec)
            else:
                rec.teacher.hash = utils.get_hash_for_teacher(rec.teacher)
                teachers[rec.teacher] = [rec]

    if request.method == 'POST':
        if request.form.get('hash'):
            teacher = utils.get_teacher_for_hash(request.form.get('hash'))
            teacher.hash = request.form.get('hash')
            utils.send_email('[Action required] Submit your AP course recommendations',
                recipient=teacher.email,
                template_name='recommendations_link',
                teacher=teacher,
                recs_count=len(teachers[teacher])
            )
            flash('Recommendation email has been sent successfully.', 'success')
            return redirect(url_for('recommendations'))

        else:
            for teacher, recs in teachers.iteritems():
                utils.send_email('[Action required] Submit your AP course recommendations',
                    recipient=teacher.email,
                    template_name='recommendations_link',
                    teacher=teacher,
                    recs_count=len(recs)
                )

            flash('Recommendation emails have been sent successfully.', 'success')
            return redirect(url_for('recommendations'))
    else:
        return render_template('recommendations.html',
            teachers=teachers,
            recs_ct={ teacher: len(recs) for teacher, recs in teachers.iteritems() },
            completed_ct={ teacher: len([rec for rec in recs if rec.status != 'pending']) for teacher, recs in teachers.iteritems() },
        )

@app.route('/recommendations/<hashed>')
def make_recommendations(hashed):
    teacher = utils.get_teacher_for_hash(hashed)

    if not teacher:
        flash( 'Invalid link!', 'errror' )
        return redirect('/')

    applications = []
    for app in models.Application.objects.order_by('teacher.name'):
        for rec in app.teacher_recs:
            if rec.teacher == teacher:
                app.relevant_rec = rec
                applications.append(app)
                continue

    return render_template('make_recommendations.html',
        teacher=teacher,
        applications=applications,
        hashed=hashed
    )

@app.route('/recommendations/<hashed>/<application_id>', methods=['POST'])
def submit_recommendation(hashed, application_id):
    application = models.Application.objects.with_id(application_id)
    teacher = utils.get_teacher_for_hash(hashed)

    recommendation = None
    for rec in application.teacher_recs:
        if rec.teacher == teacher:
            recommendation = rec
            continue

    recommendation.status = request.args['status']
    if request.args.get('rationale'):
        recommendation.rationale = request.args['rationale']

    application.save()
    return render_template('_recommendation_table_item.html',
        rec=recommendation,
        application=application,
        hashed=hashed
    )
