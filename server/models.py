from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates
from server.config import db, bcrypt
from datetime import datetime, date

class User(db.Model):
    """
    Represents a registered user in the task management system

    Stores account credentials and maintains a one-to-many
    relationship with tasks assigned to the user
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    _password_hash = db.Column(db.String, nullable=False)

    # One user can own multiple tasks
    tasks = db.relationship('Task', back_populates='user')

    @hybrid_property
    def password_hash(self):
        """
        Prevent direct access to the stored password hash
        """
        raise AttributeError("Password hashes may not be viewed")

    @password_hash.setter
    def password_hash(self, password):
        """
        Hash a plaintext password using bcrypt before storing it

        Args:
            password (str): The user's plaintext password
        """
        hashed_password = bcrypt.generate_password_hash(password)
        decoded_hashed_password = hashed_password.decode("utf-8")
        self._password_hash = decoded_hashed_password

    def authenticate(self, password):
        """
        Verify a supplied password against the stored bcrypt hash

        Args:
            password (str): Password provided during login

        Returns:
            bool: True if the password matches, otherwise False
        """
        return bcrypt.check_password_hash(self._password_hash, password)


class Task(db.Model):
    """
    Represents a task belonging to a registered user.

    Stores task details, completion status, priority, and an
    optional due date. Validators enforce valid field values
    """

    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    status = db.Column(db.String, nullable=False, default="pending")
    priority = db.Column(db.String, nullable=False, default="low")
    due_date = db.Column(db.Date)
    
    # Each task must belong to an existing user
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='tasks')


    @validates('title')
    def validate_title(self, key, title):
        """
        Ensure the task title is a non-empty string

        Raises:
            ValueError: If the title is not a string or is blank
        """
        if not isinstance(title, str):
            raise ValueError("Title must be a string")

        if not title.strip():
            raise ValueError("Title must be present")

        return title

    @validates('status')
    def validate_status(self, key, status):
        """
        Restrict task status to supported workflow states

        Allowed values:
            pending, in_progress, completed

        Raises:
            ValueError: If an unsupported status is provided
        """

        status_options = {'pending', 'in_progress', 'completed'}

        if status not in status_options:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {status_options}")

        return status

    @validates('priority')
    def validate_priority(self, key, priority):
        """
        Restrict task priority to the supported levels

        Allowed values:
            low, medium, high

        Raises:
            ValueError: If an unsupported priority is provided
        """

        priority_options = {'low', 'medium', 'high'}

        if priority not in priority_options:
            raise ValueError(f"Invalid priority '{priority}'. Must be one of: {priority_options}")

        return priority

    @validates('due_date')
    def validate_due_date(self, key, due_date):
        """
        Validate and normalize the optional task due date

        Accepts:
            - None for tasks without a due date
            - A string formatted as YYYY-MM-DD
            - A Python date object

        Returns:
            date or None: The validated date value

        Raises:
            ValueError: If the date is invalid or incorrectly formatted
        """

        # Due dates are optional
        if due_date is None:
            return None

        # Convert date strings into Python date objects
        if isinstance(due_date, str):
            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Date must be in 'YYYY-MM-DD' format")

        # Reject unsupported data types
        if not isinstance(due_date, date):
            raise ValueError('Invalid date provided')

        return due_date