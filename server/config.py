from flask_sqlalchemy import SQLAlchemy 
from flask_migrate import Migrate 
from flask_bcrypt import Bcrypt 
from flask_restful import Api
from flask import Flask
from sqlalchemy import MetaData
import os

# Initialize the Flask application
app = Flask(__name__)

# Configure session security using an environment variable
# SECRET_KEY must be defined before starting the application
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

# Configure the SQLite database and disable modification tracking
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Format JSON responses for improved readability
app.json.compact = False

# Establish consistent naming conventions for database foreign keys
# This supports predictable constraint names during migrations
metadata = MetaData(naming_convention={
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
})

# Initialize SQLAlchemy with the configured Flask application
db = SQLAlchemy(app, metadata=metadata)

# Enable database schema migrations through Flask-Migrate
migrate = Migrate(app, db)

# Initialize bcrypt for secure password hashing and verification
bcrypt = Bcrypt(app)

# Register Flask-RESTful for class-based API resources
api = Api(app)