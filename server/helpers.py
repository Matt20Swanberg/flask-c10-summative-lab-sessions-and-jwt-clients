from flask import session, request
from server.models import Task
from functools import wraps
from werkzeug.exceptions import BadRequest

def require_authentication(func):
    """
    Decorator that restricts access to authenticated users

    Checks whether a user ID exists in the Flask session
    before allowing the decorated endpoint to execute

    Args:
        func (callable): The endpoint method being protected

    Returns:
        callable: A wrapped function that returns HTTP 401
        when no authenticated session exists
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        # Retrieve the authenticated user's ID from the session
        user_id = get_current_user_id()

        if not user_id:
            return {'message': 'User not authenticated'}, 401

        # Continue to the protected endpoint
        return func(*args, **kwargs)

    return wrapper

def get_current_user_id():
    """
    Retrieve the authenticated user's ID from the Flask session

    Returns:
        int or None: The current user's ID, or None if
        no authenticated session exists
    """
    return session.get('user_id')


def get_user_task(task_id, user_id):
    """
    Retrieve a task belonging to a specific user

    Filters by both task ID and user ID to prevent users
    from accessing tasks owned by other accounts

    Args:
        task_id (int): ID of the requested task.
        user_id (int): ID of the authenticated user

    Returns:
        Task or None: The matching task, or None if no
        matching task belongs to the specified user
    """
    return Task.query.filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()


def update_task_fields(task, data):
    """
    Update a task using only permitted fields from request data

    Prevents arbitrary attributes such as task ID or user ID
    from being modified through the update endpoint

    Args:
        task (Task): The existing task instance to update
        data (dict): Incoming task attributes and values

    Returns:
        Task: The updated task instance

    Note:
        SQLAlchemy model validators are triggered when
        validated attributes are assigned
    """

    # Only these task attributes can be modified
    allowed_fields = (
        'title',
        'description',
        'status',
        'priority',
        'due_date'
    )

    for field in allowed_fields:
        if field in data:
            setattr(task, field, data[field])

    return task

def get_json_data():
    """
    Retrieve and validate the JSON body of an incoming request

    Uses silent JSON parsing to avoid raising an exception
    immediately when malformed JSON is encountered

    The parsed data must be a JSON object rather than
    a list, string, number, or null value

    Returns:
        dict: The validated JSON request body

    Raises:
        BadRequest: If the request body is missing, malformed,
        or does not contain a JSON object
    """

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise BadRequest(description="A JSON object is required")

    return data