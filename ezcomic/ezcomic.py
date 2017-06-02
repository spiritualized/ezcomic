from flask import Flask, render_template, request, redirect, url_for, session, g, send_from_directory
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Index, String, Integer, Text, DateTime, Boolean
from flask_login import login_required, current_user, LoginManager, login_user, logout_user
import user_agents
import bcrypt
import bbcode
import datetime
import random

from config import *

# flask app
app = Flask(__name__, static_folder='static')
app.debug = True
app.secret_key = secret_key

# login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# db stuff
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sqlite.db3'
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = "users"
    uid = Column('uid',db.Integer, primary_key=True)
    username = Column('username', String(20), unique=True , index=True)
    password = Column('password', String(60))

    def __init__(self, username, password):
        self.username = username
        self.password = password

    is_authenticated = True
    is_active = True
 
    def get_id(self):
        return str(self.uid)


class Post(db.Model):
    __tablename__ = "posts"
    pid = Column('pid', Integer, primary_key=True)
    date = Column('date', DateTime)
    title = Column('title', String(256))
    published = Column('published', Boolean, default=True)
    contents = Column('contents', Text)
    views = Column('views', Integer, default=0)
    bot_views = Column('bot_views', Integer, default=0)

    def __init__(self, date, title, contents):
        self.date = date
        self.title = title
        self.published = True
        self.contents = contents
        self.views = 0
        self.bot_views = 0

    def __repr__(self):
        return "%s %s %s %s" % (self.pid, self.date, self.title, self.published)

class ConfigValue(db.Model):
    __tablename__ = "config"
    key = Column(db.String(128), primary_key=True)
    value = Column(db.String(512))

    def __init__(self, key, value):
        self.key = key
        self.value = value

@login_manager.user_loader
def load_user(uid):
    return db.session.query(User).get(uid)

# populate data required for all views
def PopulateData():
    data = {
        'site_title': site_title,
    }

    if current_user.is_authenticated:
        data['button3'] = 'admin'
    elif db.session.query(User).count() > 0:
        data['button3'] = 'login'
    else:
        data['button3'] = 'reg'


    data['banner_url'] = "/static/images/banner2.png"
    banner_url = db.session.query(ConfigValue).filter_by(key="banner_url").first()
    if banner_url:
        data['banner_url'] = banner_url.value

    return data

# ensure registration passwords are of sufficiently high quality
def CheckPasswordAcceptable(password):
    if any(char.isdigit() for char in password) is False:
        return False
    if any(char.isupper() for char in password) is False:
        return False
    if any(char.islower() for char in password) is False:
        return False
    if len(password) < 8:
        return False
    return True

def date_validate(date_text):
    try:
        date = datetime.datetime.strptime(date_text, '%d/%m/%Y')
    except ValueError:
        return None
    return date

def post_swap(pid1, pid2):
    post1 = db.session.query(Post).filter_by(pid=request.args.get('pid1')).first()
    post2 = db.session.query(Post).filter_by(pid=request.args.get('pid2')).first()
    
    if post1 and post2:
        post1.pid = -1
        post2.pid = -2
        db.session.commit()
        post1.pid = request.args.get('pid2')
        post2.pid = request.args.get('pid1')
        db.session.commit()
    return redirect(url_for('admin'))


# redirect requests prefixed with "www." to base domain index
@app.before_request
def redirect_www():
    if '://www.' in request.url:
        return redirect(request.url.replace('://www.', '://'))

@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

@app.route('/')
@app.route('/<pid>')
def index(pid=-1):
    data = PopulateData()

    # check if id is an integer
    try:
        curr_post = int(pid)
    except ValueError:
        return redirect(url_for('index'))
    
    # placeholder fakepost for new users :)
    if db.session.query(Post).count() is 0:
        post = Post(datetime.datetime.now(), "Placeholder", "You need to add a comic!")
        post.pid = 1
    # latest post
    elif pid is -1:
        post = db.session.query(Post).filter_by(published=True).order_by(Post.pid.desc()).first()
    # specified post
    else:
        post = db.session.query(Post).filter_by(published=True, pid=pid).first()

        # if someone tried to retrieve a non-existant post
        if not post:
            return redirect(url_for('index'))

    # increment view count
    if not current_user.is_authenticated:
        user_agent = user_agents.parse(request.headers.get('User-Agent'))
        if user_agent.is_bot:
            post.bot_views += 1
        else:
            post.views += 1
    
        db.session.commit()

    # calculate comic IDs for navigation
    data['post_oldest'] = 0
    data['post_previous'] = 0
    data['post_next'] = 0
    data['post_newest'] = 0
    data['post_random'] = 0

    curr = db.session.query(Post).filter_by(published=True).order_by(Post.pid.asc()).first()
    if curr:
        data['post_oldest'] = curr.pid
    curr = db.session.query(Post).filter_by(published=True).order_by(Post.pid.desc()).first()
    if curr:
        data['post_newest'] = curr.pid
    curr = db.session.query(Post).filter_by(published=True).filter(Post.pid < post.pid).order_by(Post.pid.desc()).first()
    if curr:
        data['post_previous'] = curr.pid
    curr = db.session.query(Post).filter_by(published=True).filter(Post.pid > post.pid).order_by(Post.pid.asc()).first()
    if curr:
        data['post_next'] = curr.pid

    # pick a random pid (not the current one)
    if db.session.query(Post).count() > 1:
        while True:
            rand = random.randrange(0,db.session.query(Post).filter_by(published=True).count())
            data['post_random'] = db.session.query(Post).filter_by(published=True).offset(rand).first().pid

            if data['post_random'] is not post.pid:
                break


    # finally, prepare the post for templating
    if post:
        parser = bbcode.Parser(install_defaults=True, replace_links=False)
        parser.add_simple_formatter('img', '<img src="%(value)s" class="img-responsive" alt="" />')
        data['comic_html'] = parser.format(post.contents)
        data['date'] = post.date.strftime("%d %B '%y")
        data['post_curr'] = post.pid
    
    return render_template('index.html', data=data)

@app.route('/about')
def about():
    data = PopulateData()
    
    return render_template('about.html', data=data)

@app.route('/register' , methods=['GET','POST'])
def register():
    data = PopulateData()

    if request.method == 'GET':
        return render_template('register.html', data=data)

    if db.session.query(User).filter_by(username=request.form['username']).count() == 1:
        data['error'] = 'Username "%s" already exists :(' % request.form['username']
        return render_template('register.html', data=data)
    if CheckPasswordAcceptable(request.form['password']) is False:
        data['error'] = "Your password must contain a mixture of at least 8 characters: numbers, and lowercase/uppercase letters :("
        return render_template('register.html', data=data)


    hashed = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
    user = User(request.form['username'] , hashed)

    db.session.add(user)
    db.session.commit()
    login_user(user)

    return redirect(url_for('admin'))
 
@app.route('/login',methods=['GET','POST'])
def login():
    data = PopulateData()

    # if there aren't any registered users yet, redirect to registration
    if db.session.query(User).count() is 0:
        return redirect(url_for('register'))

    if request.method == 'GET':
        return render_template('login.html', data=data)

    user = db.session.query(User).filter_by(username=request.form['username']).first()

    if user is None:
        data['error'] = 'Invalid username'
        return render_template('login.html', data=data)

    if bcrypt.hashpw(request.form['password'].encode('utf-8'), user.password) != user.password:
        data['error'] = 'Invalid password'
        return render_template('login.html', data=data)
            
    login_user(user)
    return redirect(url_for('admin'))

@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    data = PopulateData()
    
    if request.method == 'GET':

        # handle id-swap operation
        if request.args.get('pid1') and request.args.get('pid2'):
            return post_swap(request.args.get('pid1'), request.args.get('pid2'))

        data['button3'] = 'logout'
        data['curr_date'] = datetime.datetime.now().strftime("%d/%m/%Y")

        data['posts'] = db.session.query(Post).order_by(Post.pid.desc()).all()

        for post in data['posts']:
            post.date = post.date.strftime("%d/%m/%Y")
            post.url = url_for('edit', pid=post.pid)

            if post.title == '':
                post.title = '(untitled)'

            # generate urls for swapping comic order
            if post.pid is not data['posts'][0].pid:
                post.move_up = url_for('admin', pid1=post.pid, pid2=post.pid+1)
            if post.pid is not data['posts'][-1].pid:
                post.move_down = url_for('admin', pid1=post.pid, pid2=post.pid-1)

        return render_template('admin.html', data=data)

    elif request.method == 'POST':
        
        if 'banner_url' in request.form:

            banner_url = request.form['banner_url']

            # force https if https in use
            if "https://" in request.url:
                banner_url = banner_url.replace("http://", "https://")

            db.session.merge(ConfigValue("banner_url", banner_url))
            db.session.commit()

        else:
            date = date_validate(request.form['date'])

            if not date:
                data['error'] = 'Invalid date'
                return render_template('admin.html', data=data)

            post = Post(date, request.form['title'], request.form['comic_bbcode'])

            db.session.add(post)
            db.session.commit()

        return redirect(url_for('index'))

@app.route('/edit/<pid>', methods=['GET', 'POST'])
@login_required
def edit(pid):
    data = PopulateData()
    
    if request.method == 'GET':
        data['button3'] = 'logout'

        post = db.session.query(Post).filter_by(pid=pid).first()
        if not(post):
            return redirect('admin')

        post.date = post.date.strftime("%d/%m/%Y")
        data['post'] = post

        return render_template('edit.html', data=data)

    date = date_validate(request.form['date'])

    if not date:
        data['error'] = 'Invalid date'
        return render_template('admin.html', data=data)

    post =  db.session.query(Post).filter_by(pid=pid).first()
    post.date = date_validate(request.form['date'])
    post.title = request.form['title']
    post.published = int(request.form['published'])
    post.contents = request.form['comic_bbcode']

    db.session.commit()
    
    return redirect(url_for('admin', pid=pid))

db.create_all()

if __name__ == '__main__':

    app.run()
