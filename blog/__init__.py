import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate



app = Flask(__name__)
app.config['SECRET_KEY'] = 'e6bb68bc99cee6dbcaff870d756284f2fe68fcf2085630d44b3206bedf7bbc55'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
loginManager = LoginManager(app)
loginManager.login_view = 'login'
loginManager.login_message_category = 'info'
migrate = Migrate(app, db)

from blog import routes, models