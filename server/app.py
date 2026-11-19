from server.config import app, db, migrate, api
from server.models import User, Task

from flask import request, session, make_response
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from server.schemas import UserSchema

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



api.add_resource(Signup, "/signup")
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Logout, '/logout', endpoint='logout')