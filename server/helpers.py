from flask import session, request
from server.models import Task
from functools import wraps
from werkzeug.exceptions import BadRequest

def require_authentication(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        user_id = get_current_user_id()

        if not user_id:
            return {'message': 'User not authenticated'}, 401

        return func(*args, **kwargs)

    return wrapper

def get_current_user_id():
    return session.get('user_id')


def get_user_task(task_id, user_id):
    return Task.query.filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()


def update_task_fields(task, data):
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
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise BadRequest(description="A JSON object is required")

    return data