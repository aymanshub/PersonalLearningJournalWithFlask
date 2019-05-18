from flask_wtf import Form
from wtforms import StringField, PasswordField, TextAreaField, DateField, \
    IntegerField
from wtforms.validators import (DataRequired, Regexp, ValidationError, Email,
                                Length, EqualTo, Optional, NumberRange)

from models import User


def name_exists(form, field):
    if User.select().where(User.username == field.data).exists():
        raise ValidationError('User with that name already exists.')


def email_exists(form, field):
    if User.select().where(User.email == field.data).exists():
        raise ValidationError('User with that email already exists.')


class RegisterForm(Form):
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Regexp(
                r'^[a-zA-Z0-9_]+$',
                message=("Username should be one word, letters, "
                         "numbers and underscores only.")
            ),
            name_exists
        ])
    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email(),
            email_exists
        ])
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=6),
            EqualTo('password2', message='Passwords must match')
        ])
    password2 = PasswordField(
        'Confirm Password',
        validators=[DataRequired()]
    )


class LoginForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


class JEntryForm(Form):
    title = StringField("Title", validators=[DataRequired()])
    date = DateField("Date", validators=[Optional()], format='%d/%m/%Y')
    time_spent = IntegerField(
        "Time Spent",
        validators=[
            DataRequired(message='Time should be a whole (non-zero) positive'
                                 ' number representing the spent hours!'
                         ),
            NumberRange(min=1)
        ])
    learned = TextAreaField(
        'What You Learned?',
        validators=[
            DataRequired(message='Please enter the things you\'ve learned')
        ])
    resources = TextAreaField(
        'Resources',
        validators=[
            DataRequired(message='Please enter the resources you\'ve used')
        ])
    tags = StringField("Tags", validators=[Optional()])

