"""
Python Web Development Techdegree
Project 5 - Personal Learning Journal With Flask
--------------------------------
Developed by: Ayman Said
May-2019
"""
import datetime
import re

from flask import (Flask, g, render_template, flash, redirect, url_for,
                   abort, request)
from flask_bcrypt import check_password_hash
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)

import forms
import models

DEBUG = True
PORT = 8006
HOST = 'localhost'

app = Flask(__name__)
app.secret_key = 'ThisIsASuperDuperSecretKeyPleaseDoNotTell!'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    try:
        return models.User.get(models.User.id == user_id)
    except models.DoesNotExist:
        return None


@app.before_request
def before_request():
    """Connect to the database before each request."""
    g.db = models.DATABASE
    g.db.connect()
    g.user = current_user


@app.after_request
def after_request(response):
    """Close the database connection after each request"""
    g.db.close()
    return response


@app.route('/register', methods=('GET', 'POST'))
def register():
    """
    Register view for new users who'd like to register
    :return: a rendered register.html template
    """
    form = forms.RegisterForm()
    if form.validate_on_submit():
        try:
            models.User.create_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
            )
        except ValueError as e:
            flash("{}".format(e), "error")
        else:
            flash("Welcome, you registered!", "success")
        return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login view for the registered users
    :return: a rendered login.html template
    """
    form = forms.LoginForm()
    if form.validate_on_submit():
        try:
            user = models.User.get(models.User.email ** form.email.data)
        except models.DoesNotExist:
            flash("You email or password doesn't match", "error")
        else:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                flash("You've been logged in!", "success")
                return redirect(url_for('index'))
            else:
                flash("Your email or password doesn't match", "error")
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """
    Logout view for logged-in user
    :return: redirect to the index view
    """
    logout_user()
    flash("You've been logged out!", "success")
    return redirect(url_for('index'))


@app.route('/entries/<slug>/edit', methods=['GET', 'POST'])  # The Edit route
@login_required
def edit(slug):
    """
    Edit entry view, for the logged-in entry owner user.
    All entry content fields can be modified.
    :param slug: Charfield Entry Model value, entry identifier
    :return: a rendered edit.html template page for the selected entry
    """
    entry = models.Entry.get(models.Entry.slug == slug)
    # Security check: Only entry owner can edit the entry
    if g.user.id != entry.user.id:
        flash("You can't edit this entry \
                    only entry owner can edit it!", "error")
    else:
        # parse entry.tags object to string, for form display matter
        entry.tags = '#'.join([tag.tag for tag in entry.tags])
        form = forms.JEntryForm(request.values, obj=entry)
        if form.validate_on_submit():
            entry.title = form.title.data
            # non unicode word character(white-spaces),
            # is substituted by a hyphen.
            entry.slug = re.sub(r'[^\w]+', '-',
                                form.title.data.lower()).strip('-')
            entry.date = form.date.data \
                if form.date.data else datetime.date.today()
            entry.time_spent = form.time_spent.data
            entry.learned = form.learned.data
            entry.resources = form.resources.data
            try:
                entry.save()
            except models.IntegrityError:
                raise ValueError("User already exists!")

            # list the unique tags, before the edit and on submission
            old_tags = list(dict.fromkeys(filter(None,
                                                 entry.tags.split("#"))))
            new_tags = list(dict.fromkeys(filter(None,
                                                 form.tags.data.split("#"))))

            # sorts out what tags need to be added and deleted
            delete_tags, add_tags = tags_ordinator(old_tags, new_tags)

            # delete the old tags
            q = models.Tag.delete().where(
                (models.Tag.entry_id == entry.id) &
                (models.Tag.tag << delete_tags)
            )
            q.execute()

            # adds the new tags
            if add_tags:
                for tag in add_tags:
                    models.Tag.create(
                        tag=tag,
                        entry=entry
                    )
            flash("entry has successfully been edited.".capitalize(),
                  "success")
            return redirect(url_for('index'))
        return render_template('edit.html', form=form)

    return redirect(url_for('detail', slug=entry.slug))


@app.route('/entries/<slug>/delete')  # Delete route
@login_required
def delete(slug):
    """
    Deletes the entry from the Entry model.
    :param slug: Charfield Entry Model value, entry identifier
    :return: if the entry owner returns the user to the index view,
    else, to the entry detail page.
    """
    # verifies if entry exists in the model, before deletion
    try:
        entry = models.Entry.get(models.Entry.slug == slug)
    except models.DoesNotExist:
        abort(404)
    else:
        # Security check: Only entry owner can delete the entry
        if g.user.id != entry.user.id:
            flash("You can't delete this entry \
            only entry owner can delete it!", "error")
        else:
            try:
                # Deletes the entry and it's related tags
                models.Entry.get(models.Entry.id == entry.id) \
                    .delete_instance(recursive=True, delete_nullable=True)
            except models.IntegrityError:
                pass
            else:
                flash("Entry has been successfully deleted!", "success")
            return redirect(url_for('index'))
        return redirect(url_for('detail', slug=entry.slug))


@app.route('/entries/<slug>')  # Detail route
def detail(slug):
    """
    Entry detail view, displays the entry content
    according to the detail.html template.
    :param slug: Charfield Entry Model value, entry identifier.
    :return: A rendered detail.html template page for the selected entry.
    """
    try:
        entry = models.Entry.get(models.Entry.slug == slug)
    except models.DoesNotExist:
        abort(404)
    else:
        return render_template('detail.html', entry=entry)


@app.route('/entries/new', methods=('GET', 'POST'))
@login_required
def new():
    """
    New entry view, for the logged-in user.
    :return: redirects to the index page.
    If one of the required fields was not filled will stay on the same view.
    """
    form = forms.JEntryForm()
    if form.validate_on_submit():
        try:
            entry = models.Entry.create_entry(
                title=form.title.data,
                date=form.date.data,
                time_spent=form.time_spent.data,
                learned=form.learned.data,
                resources=form.resources.data,
                user=g.user._get_current_object(),
            )
        except ValueError as e:
            flash("{}".format(e), "error")
        else:
            if form.tags.data:
                # lists the unique tags provided in the entry creation
                tags = list(dict.fromkeys(filter(None,
                                                 form.tags.data.split("#"))))

                for tag in tags:
                    models.Tag.create(
                        tag=tag,
                        entry=entry
                    )
            flash("entry has successfully been published.".capitalize(),
                  "success")
        return redirect(url_for('index'))
    return render_template('new.html', form=form)


@app.route('/')
@app.route('/entries')
def index():
    """
    The blog main page view, it lists all existing entries
    from the Entry model.
    :return: a rendered page of edit.html template.
    """
    entries = models.Entry.select()
    return render_template('index.html', entries=entries)


@app.route('/entries/by-tag/<tag>')
def tagged_entries(tag):
    """
    Lists all entries having the same tag parameter.
    :param tag: CharField Tag Model value
    :return: a rendered index.html template
    listing the given related tag entries.
    """
    entries = models.Entry.select().join(models.Tag) \
        .where(models.Tag.tag == tag).order_by(models.Entry.id)
    return render_template('index.html', entries=entries)


def tags_ordinator(old_list, new_list):
    """Helps verify what tags need to deleted and what need to be added
    leaving the common unchanged in the Tag Model.
    :param old_list: entry old tags list before the edit process
    :param new_list: entry new tags list after the edit process
    :return:
            delete_tags, a list represents the new tags need to be deleted.
            add_tags, a list represents the new tags need to be added.
    """
    delete_tags = []
    add_tags = []
    for tag in old_list:
        if tag not in new_list:
            delete_tags.append(tag)
    for tag in new_list:
        if tag not in old_list:
            add_tags.append(tag)
    return delete_tags, add_tags


@app.errorhandler(404)
def not_found(error):
    """
    Error page view for any not found requested route.
    :return: A rendered 404.html template.
    """
    return render_template('404.html'), 404


if __name__ == '__main__':
    # initializing the Data-Base and Models
    models.initialize()
    # Running the Flask Web App, according to the given parameters
    app.run(debug=DEBUG, host=HOST, port=PORT)
