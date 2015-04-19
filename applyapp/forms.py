from flask_wtf import Form
from wtforms import TextField, TextAreaField, SubmitField, SelectField, BooleanField, FileField, PasswordField, SelectMultipleField, \
    FieldList, FormField, widgets, validators
from flask.ext.pagedown.fields import PageDownField

from bson import ObjectId

class SecurePasswordInput(widgets.PasswordInput):
    def __call__(self, field, **kwargs):
        kwargs['autocomplete'] = 'off'
        return super(SecurePasswordInput, self).__call__(field, **kwargs)

class UserEditForm(Form):
    email = TextField('Email address',[validators.Required(), validators.Email(message='That\'s not a valid email address.')])
    password = PasswordField('Password (leave blank to keep unchanged)', [validators.EqualTo('confirm_password', message='Passwords must match.')], widget=SecurePasswordInput())
    confirm_password = PasswordField('Confirm password', widget=SecurePasswordInput())
    roles = SelectMultipleField('User roles', widget=widgets.ListWidget(prefix_label=False), option_widget=widgets.CheckboxInput())

    submit = SubmitField('Update account details')

class CourseEditForm(Form):
    name = TextField('Course name', [validators.Required()])
    description = PageDownField('Course description')
    requirements = PageDownField('Application requirements')
    upload_required = BooleanField('File upload is required')
    open_for_applications = BooleanField('Open for applications', default=False)

    submit = SubmitField('Update course')

class TeacherEditForm(Form):
    name = TextField('Teacher name',[validators.Required()])
    email = TextField('Email address')
    is_pseudo = BooleanField('Do not allow students to select')
    submit = SubmitField('Update teacher')

class TeacherAddBulkForm(Form):
    raw = TextAreaField('Raw data')
    submit = SubmitField('Update teachers')

class ApplicationFormStep_New(Form):
    name = TextField('Full name',[validators.Required()])
    email = TextField('Email address',[validators.Required(), validators.Email(message='That\'s not a valid email address.')])
    password = PasswordField('New password', [validators.EqualTo('confirm_password', message='Passwords must match.')], widget=SecurePasswordInput())
    confirm_password = PasswordField('Confirm password', widget=SecurePasswordInput())
    submit = SubmitField('Next')

class ApplicationFormStep_UserDetail(Form):
    phone_number = TextField('Phone number')

    parent_name = TextField('Parent name')
    parent_phone_number = TextField('Parent phone number')
    parent_email = TextField('Parent email address')

    entering_grade = SelectField('Entering grade', coerce=int, choices=[(0, 'Select grade'), (9, '9th'), (10, '10th'), (11, '11th'), (12, '12th')], default=(0, 'Select grade'))
    is_first_year_at_wshs = BooleanField('This will be my first year at White Station High School')

    test_scores = TextField('Test scores', description='Please indicate recent test scores (PSAT, PLAN, Explore, ACT, or SAT) in percentile format, both in critical reading AND math.')

    taking_ap_courses = BooleanField('I am currently enrolled in one or more AP courses', default=False)
    current_ap_courses = TextField('Current AP courses', description='List only courses for the current academic year; separate with commas.')

    prev = SubmitField('Previous')
    save = SubmitField('Save')
    submit = SubmitField('Next')

class ApplicationFormStep_Courses(Form):
    desired_courses = SelectMultipleField('I wish to apply for the following AP courses:',
        coerce=ObjectId,
        widget=widgets.ListWidget(prefix_label=False), option_widget=widgets.CheckboxInput()
    )

    prev = SubmitField('Previous')
    save = SubmitField('Save')
    submit = SubmitField('Next')

class ApplicationFormStep_Course(Form):
    average_okay = BooleanField('I have at least a "B" in the listed prerequisites or similar courses.', default=False)
    have_met_reqs = BooleanField('I have met the application requirements for this course.', default=False)
    prev = SubmitField('Previous')
    save = SubmitField('Save')
    submit = SubmitField('Next')

class ApplicationFormStep_FirstYear(Form):
    understand = BooleanField(('I have downloaded the teacher recommendation form and understand that I must return it to White Station High School, completed, '
        'by the application deadline. If I do not return the form to White Station High School by this deadline, I understand that my application will be invalidated.'),
        default=False)
    prev = SubmitField('Previous')
    save = SubmitField('Save')
    submit = SubmitField('Next')

class ApplicationFormStep_Recs(Form):
    teacher_recs = SelectMultipleField('Teacher recommendations',
        coerce=ObjectId)
    confirm_contacted = BooleanField('I have personally contacted TEACHER_NAME, and he/she has consented to provide a recommendation for me.')

    prev = SubmitField('Previous')
    save = SubmitField('Save')
    submit = SubmitField('Next')

class ApplicationFormStep_Final(Form):
    confirmation_initials_student = TextField(('I understand that this AP course will require extra time and effort and I am prepared to make this commitment. '
        'I understand that I must take the corresponding AP exams. I am aware that students who are enrolled in an AP course must pay for each exam. I will be required ' +
        'to sign contracts for each AP course I take.'), description='Student initials')

    confirmation_initials_parent = TextField(('I understand that this AP course will require extra time and effort on behalf of my student and I am prepared to make this commitment. '
        'I understand that my student must take the corresponding AP exams. I am aware that students who are enrolled in an AP course must pay for each exam. I will be required ' +
        'to sign contracts for each AP course my student takes.'), description='Parent initials')

    prev = SubmitField('Previous')
    save = SubmitField('Save')
    submit = SubmitField('Submit*')
