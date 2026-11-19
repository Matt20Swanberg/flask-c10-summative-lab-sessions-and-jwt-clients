from server.config import app, db, migrate, api
from server.models import User, Task
from server.helpers import update_task_fields

from flask import request, session, make_response
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError, StatementError
from server.schemas import UserSchema, TaskSchema

class Signup(Resource):

    def post(self):
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return {"message": "A JSON object is required"}, 400

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

        data = request.get_json(silent=True)
        
        if not isinstance(data, dict):
            return {"message": "A JSON object is required"}, 400

        username = data.get('username')
        password = data.get('password')

        if not isinstance(username, str) or not isinstance(password, str):
            return {"message": "Invalid username or password"}, 401

        username = username.strip()

        user = User.query.filter(User.username == username).first()

        if user and user.authenticate(password):

            session['user_id'] = user.id

            return UserSchema().dump(user), 200

        return {'message': 'Invalid username or password'}, 401

class CheckSession(Resource):
    def get(self):
        user_id = session.get('user_id')

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
    def get(self):

        user_id = session.get('user_id')

        if not user_id:
            return {'message': 'User not authenticated'}, 401

        tasks = Task.query.filter(Task.user_id == user_id).all()

        task_json = TaskSchema(many=True).dump(tasks)

        return task_json

    def post(self):
        user_id = session.get('user_id')
        
        if not user_id:
            return {'message': 'User not authenticated'}, 401

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return {'message': 'A JSON object is required'}, 400

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

        except IntegrityError:
            db.session.rollback()
            return {"message": "Unable to create task"}, 422

        except ValueError as error:
            db.session.rollback()
            return {"message": str(error)}, 422

class TaskById(Resource):
    def get(self, id):

        user_id = session.get('user_id')

        if not user_id:
            return {'message': 'User not authenticated'}, 401

        task = Task.query.filter(
            Task.id == id,
            Task.user_id == user_id
        ).first()

        if not task:
            return {'message': 'Task not found'}, 404
        
        task_json = TaskSchema().dump(task)
        
        return task_json, 200        


    def patch(self, id):
        user_id = session.get('user_id')
        
        if not user_id:
            return {'message': 'User not authenticated'}, 401

        task = Task.query.filter(
            Task.id == id,
            Task.user_id == user_id
        ).first()

        if not task:
            return {'message': 'Task not found'}, 404

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return {'message': 'A JSON object is required'}, 400

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

    def delete(self, id):
        user_id = session.get('user_id')

        if not user_id:
            return {'message': 'User not authenticated'}, 401

        task = Task.query.filter(
            Task.id == id,
            Task.user_id == user_id
        ).first()

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