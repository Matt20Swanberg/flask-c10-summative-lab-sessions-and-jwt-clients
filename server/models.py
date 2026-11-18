from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates
from server.config import db, bcrypt
from datetime import datetime, date

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    _password_hash = db.Column(db.String, nullable=False)

    tasks = db.relationship('Task', back_populates='user')

    @hybrid_property
    def password_hash(self):
        raise AttributeError("Password hashes may not be viewed")

    @password_hash.setter
    def password_hash(self, password):
        hashed_password = bcrypt.generate_password_hash(password)
        decoded_hashed_password = hashed_password.decode("utf-8")
        self._password_hash = decoded_hashed_password

    def authenticate(self, password):
        return bcrypt.check_password_hash(self._password_hash, password)

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    status = db.Column(db.String, nullable=False, default="pending")
    priority = db.Column(db.String, nullable=False, default="low")
    due_date = db.Column(db.Date)
    

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='tasks')

    @validates('title')
    def validate_title(self, key, title):
        if not isinstance(title, str):
            raise ValueError("Title must be a string")

        if not title.strip():
            raise ValueError("Title must be present")

        return title

    @validates('status')
    def validate_status(self, key, status):
        status_options = {'pending', 'in_progress', 'completed'}

        if status not in status_options:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {status_options}")

        return status

    @validates('priority')
    def validate_priority(self, key, priority):
        priority_options = {'low', 'medium', 'high'}

        if priority not in priority_options:
            raise ValueError(f"Invalid priority '{priority}'. Must be one of: {priority_options}")

        return priority

    @validates('due_date')
    def validate_due_date(self, key, due_date):

        if due_date is None:
            return None
        
        if isinstance(due_date, str):
            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Date must be in 'YYYY-MM-DD' format")

        if not isinstance(due_date, date):
            raise ValueError('Invalid date provided')

        return due_date