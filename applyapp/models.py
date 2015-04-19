from flask.ext.mongoengine import MongoEngine
from flask.ext.security import UserMixin, RoleMixin

from core import db

class Role(db.Document, RoleMixin):
    """A role given to a user."""

    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(max_length=255)

class User(db.Document, UserMixin):
    """A user account object."""

    name = db.StringField(max_length=255)
    email = db.EmailField(max_length=255, unique=True)
    password = db.StringField(max_length=255)

    phone_number = db.StringField(max_length=255)

    parent_name = db.StringField(max_length=255)
    parent_phone_number = db.StringField(max_length=255)
    parent_email = db.StringField(max_length=255)

    entering_grade = db.IntField()
    is_first_year_at_wshs = db.BooleanField(default=False)

    roles = db.SortedListField(db.ReferenceField(Role), default=[])

    active = db.BooleanField(default=True)

class Course(db.Document):
    """An AP course."""

    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(default='')
    requirements = db.StringField(default='')
    upload_required = db.BooleanField(default=False)
    open_for_applications = db.BooleanField(default=False)

class Teacher(db.Document):
    """A teacher."""
    name = db.StringField(unique=True)
    email = db.StringField(required=False)
    is_pseudo = db.BooleanField(default=False)

class TeacherRec(db.EmbeddedDocument):
    """A particular recommendation from a teacher about a student."""
    teacher = db.ReferenceField(Teacher)
    # Status: pending, recommend, withreservations, donotrecommend 
    status = db.StringField(default='pending')
    rationale = db.StringField()

class CourseApplication(db.EmbeddedDocument):
    """An application to a course."""

    course = db.ReferenceField(Course)
    uploaded_content = db.ListField(db.FileField())
    average_okay = db.BooleanField(default=False)
    have_met_reqs = db.BooleanField(default=False)
    # Status: pending, yes, maybe, no, nosampleprovided 
    writing_sample_status = db.StringField(default='pending')
    # Status: pending, approved, rejected
    status = db.StringField(default='pending')

class Application(db.Document):
    """An application."""

    submitter = db.ReferenceField(User)
    is_submitted = db.BooleanField(default=False)
    submit_date = db.DateTimeField()

    course_applications = db.EmbeddedDocumentListField(CourseApplication)
    taking_ap_courses = db.BooleanField(default=False)
    current_ap_courses = db.StringField(default='')
    test_scores = db.StringField(default='')
    teacher_recs = db.EmbeddedDocumentListField(TeacherRec)
    confirm_contacted_teachers = db.BooleanField(default=False)
