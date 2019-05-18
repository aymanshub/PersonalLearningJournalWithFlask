import datetime
import re

from flask_bcrypt import generate_password_hash
from flask_login import UserMixin
from peewee import *

#DATABASE = SqliteDatabase('social.db')
DATABASE = SqliteDatabase('social.db', pragmas={'foreign_keys': 1})


class User(UserMixin, Model):
    username = CharField(unique=True)
    email = CharField(unique=True)
    password = CharField(max_length=100)
    joined_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = DATABASE
        order_by = ('-joined_at',)

    @classmethod
    def create_user(cls, username, email, password):
        try:
            with DATABASE.transaction():
                cls.create(
                    username=username,
                    email=email,
                    password=generate_password_hash(password)
                )
        except IntegrityError:
            raise ValueError("User already exists!")


class Entry(Model):
    title = CharField()
    slug = CharField(unique=True)
    date = DateField(default=datetime.date.today)
    time_spent = IntegerField(default=0)
    learned = TextField()
    resources = TextField()
    user = ForeignKeyField(model=User, backref='entries')

    class Meta:
        database = DATABASE
        order_by = ('-date',)

    @classmethod
    def create_entry(cls, title, date, time_spent, learned, resources, user):
        # create a friendly URL using regX
        slug = re.sub(r'[^\w]+', '-', title.lower()).strip('-')
        if not date:
            date = datetime.date.today()
        try:
            with DATABASE.transaction():
                return cls.create(
                            title=title,
                            slug=slug,
                            date=date,
                            time_spent=time_spent,
                            learned=learned,
                            resources=resources,
                            user=user,
                )
        except IntegrityError:
            raise ValueError("Entry with the same title already exists!")


class Tag(Model):
    tag = CharField()
    entry = ForeignKeyField(model=Entry, backref='tags')

    class Meta:
        database = DATABASE


def initialize():
    DATABASE.connect()
    DATABASE.create_tables([User, Entry, Tag], safe=True)
    DATABASE.close()
