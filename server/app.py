from server.config import app, db, migrate, api
from server.models import User, Task
from server.helpers import (
    get_current_user_id,
    get_user_task,
    update_task_fields,
    require_authentication,
    get_json_data
)

from flask import request, session, make_response
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError, StatementError
from server.schemas import UserSchema, TaskSchema
from werkzeug.exceptions import BadRequest

@app.errorhandler(BadRequest)
def handle_bad_request(error):
    return {'message': error.description}, 400

class Signup(Resource):

    def post(self):
        data = get_json_data()

        username = data.get("username")
        password = data.get("password")

        try:
            if not isinstance(username, str) or not username.strip():
                raise ValueError("Username cannot be empty")
            if not isinstance(password, str) or not password.strip():
                raise ValueError("Password cannot be empty")

            username = username.strip()

            new_user = User(
                username=username
            )

            new_user.password_hash = password

            db.session.add(new_user)
            db.session.commit()

            session["user_id"] = new_user.id

            user_json = UserSchema().dump(new_user)

            return user_json, 201

        except IntegrityError:
            db.session.rollback()
            return {"message": "Username already exists"}, 422

        except ValueError as error:
            db.session.rollback()
            return {"message": str(error)}, 422

class Login(Resource):
    def post(self):

        data = get_json_data()

        username = data.get('username')
        password = data.get('password')

        if not isinstance(username, str) or not isinstance(password, str):
            return {
                "message": "Invalid username or password",
                "errors": ["Invalid username or password"]
            }, 401

        username = username.strip()

        user = User.query.filter(User.username == username).first()

        if user and user.authenticate(password):

            session['user_id'] = user.id

            return UserSchema().dump(user), 200

        return {
            'errors': ['Invalid username or password'],
            'message': 'Invalid username or password'
        }, 401

class CheckSession(Resource):
    def get(self):
        user_id = get_current_user_id()

        if user_id:
            user = User.query.filter(User.id == user_id).first()

            if user is not None:
                return UserSchema().dump(user), 200

        return {"message": "Unauthorized access"}, 401

class Logout(Resource):
    def delete(self):
        session.pop('user_id', None)
        return '', 204

class Tasks(Resource):
    @require_authentication
    def get(self):
        
        user_id = get_current_user_id()
        
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        if 'page' not in request.args:
            page = 1

        if 'per_page' not in request.args:
            per_page = 5

        if (
            page is None
            or per_page is None
            or page < 1 
            or per_page < 1
        ):
            return {'message': 'Page and per_page must be positive integers'}, 400

        pagination = Task.query.filter(
            Task.user_id == user_id
            ).order_by(Task.id).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

        tasks = TaskSchema(many=True).dump(pagination.items)

        response_data = {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
            "items": tasks,
        }

        return response_data, 200
    
    @require_authentication
    def post(self):
        user_id = get_current_user_id()

        data = get_json_data()

        title = data.get('title')
        description = data.get('description')
        status = data.get('status', 'pending')
        priority = data.get('priority', 'low')
        due_date = data.get('due_date')

        try:
            new_task = Task(
                title=title,
                description=description,
                status=status,
                priority=priority,
                due_date=due_date,
                user_id=user_id
            )

            db.session.add(new_task)
            db.session.commit()

            task_json = TaskSchema().dump(new_task)
            return task_json, 201

        except (IntegrityError, StatementError):
            db.session.rollback()
            return {"message": "Unable to create task"}, 422

        except ValueError as error:
            db.session.rollback()
            return {"message": str(error)}, 422

class TaskById(Resource):
    @require_authentication
    def get(self, id):

        user_id = get_current_user_id()

        task = get_user_task(id, user_id)

        if not task:
            return {'message': 'Task not found'}, 404
        
        task_json = TaskSchema().dump(task)
        
        return task_json, 200        

    @require_authentication
    def patch(self, id):
        user_id = get_current_user_id()

        task = get_user_task(id, user_id)

        if not task:
            return {'message': 'Task not found'}, 404

        data = get_json_data()

        try:
            update_task_fields(task, data)

            db.session.commit()

            return TaskSchema().dump(task), 200

        except ValueError as error:
            db.session.rollback()
            return {'message': str(error)}, 422

        except (IntegrityError, StatementError):
            db.session.rollback()
            return {'message': 'Unable to update task'}, 422

    @require_authentication
    def delete(self, id):
        user_id = get_current_user_id()

        task = get_user_task(id, user_id)

        if not task:
            return {'message': 'Task not found'}, 404

        db.session.delete(task)
        db.session.commit()

        return '', 204


api.add_resource(Signup, "/signup")
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Logout, '/logout', endpoint='logout')

api.add_resource(Tasks, '/tasks', endpoint='tasks')
api.add_resource(TaskById, '/tasks/<int:id>', endpoint='task_by_id')