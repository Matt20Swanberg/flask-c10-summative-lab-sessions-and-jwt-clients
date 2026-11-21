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
    """
    Handle malformed or invalid JSON requests.

    Returns:
        tuple: An error message and HTTP 400 status code.
    """
    return {'message': error.description}, 400

class Signup(Resource):
    """
    Handle user registration and account creation.
    """

    def post(self):
        """
        Register a new user and establish an authenticated session.

        Validates the username and password, hashes the password,
        saves the new account, and stores the user's ID in the session.

        Returns:
            201: Serialized user data after successful registration.
            422: Invalid input or a duplicate username.
            400: Invalid JSON request body.
        """
        data = get_json_data()

        username = data.get("username")
        password = data.get("password")
        password_confirmation = data.get("password_confirmation")

        try:
            if not isinstance(username, str) or not username.strip():
                raise ValueError("Username cannot be empty")
            if not isinstance(password, str) or not password.strip():
                raise ValueError("Password cannot be empty")

            # Ensure the password confirmation matches before creating the user
            if password != password_confirmation:
                raise ValueError("Passwords do not match")

            username = username.strip()

            new_user = User(
                username=username
            )

            # Hash the password through the User model setter
            new_user.password_hash = password

            db.session.add(new_user)
            db.session.commit()

            # Automatically authenticate the newly registered user
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
    """
    Authenticate existing users through session-based login.
    """

    def post(self):
        """
        Validate user credentials and establish a login session.

        Returns:
            200: Serialized user data after successful login.
            401: Invalid username or password.
            400: Invalid JSON request body.

        Note:
            Error responses include both 'message' and 'errors'
            to support backend tests and React form validation.
        """

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
    """
    Verify whether an authenticated user session exists.
    """

    def get(self):
        """
        Retrieve the currently authenticated user's information.

        Returns:
            200: Serialized user data for an active session.
            401: No valid authenticated user session.
        """
        user_id = get_current_user_id()

        if user_id:
            user = User.query.filter(User.id == user_id).first()

            if user is not None:
                return UserSchema().dump(user), 200

        return {"message": "Unauthorized access"}, 401

class Logout(Resource):
    """
    Handle user logout and session cleanup.
    """
    def delete(self):
        """
        Remove the authenticated user ID from the session.

        Returns:
            204: Successful logout with no response body.
        """
        session.pop('user_id', None)
        return '', 204

class Tasks(Resource):
    """
    Handle collection-level task operations.

    Supports retrieving paginated tasks and creating new tasks
    for the currently authenticated user.
    """
     
    @require_authentication
    def get(self):
        """
        Retrieve a paginated list of the current user's tasks.

        Query Parameters:
            page (int): Page number, defaults to 1.
            per_page (int): Tasks per page, defaults to 5.

        Returns:
            200: Paginated task data and pagination metadata.
            400: Invalid pagination parameters.
            401: User is not authenticated.
        """        
        user_id = get_current_user_id()
        
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        # Apply defaults only when parameters are omitted
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

        # Restrict results to the authenticated user's tasks
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
        """
        Create a new task owned by the authenticated user.

        Uses default values for status and priority when
        they are not included in the request body.

        Returns:
            201: Serialized data for the newly created task.
            422: Invalid task data or database constraint failure.
            400: Invalid JSON request body.
            401: User is not authenticated.
        """
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
    """
    Handle operations on individual tasks.

    All operations require authentication and verify task
    ownership before allowing access or modifications.
    """

    @require_authentication
    def get(self, id):
        """
        Retrieve a task by ID if it belongs to the current user.

        Returns:
            200: Serialized task data.
            401: User is not authenticated.
            404: Task does not exist or belongs to another user.
        """
        user_id = get_current_user_id()

        task = get_user_task(id, user_id)

        if not task:
            return {'message': 'Task not found'}, 404
        
        task_json = TaskSchema().dump(task)
        
        return task_json, 200        

    @require_authentication
    def patch(self, id):
        """
        Update permitted fields on a task owned by the user.

        Uses the update_task_fields helper to prevent changes
        to protected attributes such as user_id.

        Returns:
            200: Updated serialized task data.
            400: Invalid JSON request body.
            401: User is not authenticated.
            404: Task does not exist or belongs to another user.
            422: Invalid task data or database constraint failure.
        """
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
        """
        Delete a task owned by the authenticated user.

        Returns:
            204: Task deleted successfully.
            401: User is not authenticated.
            404: Task does not exist or belongs to another user.
        """
        user_id = get_current_user_id()

        task = get_user_task(id, user_id)

        if not task:
            return {'message': 'Task not found'}, 404

        db.session.delete(task)
        db.session.commit()

        return '', 204


# Register authentication endpoints
api.add_resource(Signup, "/signup")
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Logout, '/logout', endpoint='logout')

# Register task management endpoints
api.add_resource(Tasks, '/tasks', endpoint='tasks')
api.add_resource(TaskById, '/tasks/<int:id>', endpoint='task_by_id')