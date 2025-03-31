from flask import Flask, render_template, request,redirect
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
import json
from werkzeug.utils import secure_filename

from datetime import datetime
import os
from flask import session
import math

# Load configuration
params = {}
try:
    with open('config.json', 'r') as c:
        params = json.load(c)["params"]
except (FileNotFoundError, KeyError):
    print("Error: config.json file not found or invalid format!")

# Boolean check for local server
local_server = True  # Corrected from "True" (string)

app = Flask(__name__)
app.secret_key='super-secret-key'
app.config['UPLOAD_FOLDER']=params["folder_location"]
# Mail Configuration
if params:
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=465,
        MAIL_USE_SSL=True,
        MAIL_USERNAME=params.get('gmail-user'),
        MAIL_PASSWORD=params.get('gmail-password')
    )

mail = Mail(app)

# Database Configuration
if local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = params.get('local_uri')
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params.get('prod_uri')

db = SQLAlchemy(app)

# Models
class Contacts(db.Model):
    __tablename__ = 'contactdetail'
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)

class Posts(db.Model):
    __tablename__ = 'posts'
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(1000), nullable=False)  # Changed from String(120)
    date = db.Column(db.String(12), nullable=True)

# Routes
@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts) / int(params['no_of_posts']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page - 1) * int(params['no_of_posts']):(page - 1) * int(params['no_of_posts']) + int(params['no_of_posts'])]
    if page == 1:
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif page == last:
      prev = "/?page=" + str(page - 1)
      next = "#"
    else:
       prev = "/?page=" + str(page - 1)
       next = "/?page=" + str(page + 1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route("/about")
def about():
    return render_template('about.html', params=params)

@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if "user" in session and session['user'] == params['admin_user']:
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    if request.method == "POST":
        username = request.form.get("uname")
        userpass = request.form.get("upass")

        if username == params['admin_user'] and userpass == params['admin_password']:
            session['user'] = username
            posts = Posts.query.all()
            return render_template("dashboard.html", params=params, posts=posts)

    return render_template("login.html", params=params)


@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    if not post:
        print(f"Post not found for slug: {post_slug}")
        return "Post Not Found", 404
    return render_template('post.html', params=params, post=post)

@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        entry = Contacts(name=name, phone_num=phone, msg=message, date=datetime.now(), email=email)
        db.session.add(entry)
        db.session.commit()

        if params:
            mail.send_message(
                'New message from ' + name,
                sender=email,
                recipients=[params.get('gmail-user')],
                body=message + "\n" + phone
            )

    return render_template('contact.html', params=params)

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/dashboard')

@app.route("/delete/<string:sno>" , methods=['GET', 'POST'])
def delete(sno):
    if "user" in session and session['user']==params['admin_user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")


@app.route("/uploader" , methods=['GET', 'POST'])
def uploader():
    if "user" in session and session['user']==params['admin_user']:
        if request.method=='POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded successfully!"

@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if "user" in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            box_title = request.form.get('title')

            slug = request.form.get('slug')
            content = request.form.get('content')
            date = datetime.now()
            if sno == '0':
               post = Posts(title=box_title, slug=slug, content=content, date=date)
               db.session.add(post)
               db.session.commit()
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.box_title = box_title

                post.slug = slug
                post.content = content

                post.date = date
                db.session.commit()
                return redirect('/edit/' + sno)
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html',params=params,post=post,sno=sno)

# Run the app safely
if __name__ == "__main__":
    app.run(debug=True)
