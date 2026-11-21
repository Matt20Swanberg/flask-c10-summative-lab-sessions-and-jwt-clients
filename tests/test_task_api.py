"""
Automated tests for the Task Management REST API.

Tests cover:
- User registration and session authentication
- Task updates and deletion
- Task validation and database rollback behavior
- Task ownership and user isolation
- Pagination and invalid query parameters

Each test uses an isolated SQLite database to prevent changes
to the development database.
"""

import os

# Provide a development-only secret key before importing Flask
os.environ.setdefault('SECRET_KEY', 'pytest-only-secret-key')

import pytest
from sqlalchemy import create_engine

from server.app import app
from server.config import db
from server.models import User, Task


# --------------------------------------------------
# Test Fixtures
# --------------------------------------------------

@pytest.fixture
def client(tmp_path):
    """
    Create an isolated Flask test client and SQLite database.

    The temporary database is initialized before each test.
    Database tables and connections are cleaned up afterward,
    and the original database engine is restored.
    """
    app.config.update(
        TESTING=True,
        SECRET_KEY='pytest-only-secret-key'
    )

    test_engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")

    with app.app_context():
        original_engine = db.engines[None]

        # Remove existing sessions before switching databases
        db.session.remove()
        db.engines[None] = test_engine

        try:
            db.create_all()

            with app.test_client() as test_client:
                yield test_client

        finally:
            # Clean up test data and restore the original engine
            db.session.remove()
            db.drop_all()
            db.engines[None] = original_engine
            test_engine.dispose()


@pytest.fixture
def users(client):
    """
    Create two test users with securely hashed passwords.

    Returns a dictionary containing their database IDs
    for use in authentication and ownership tests.
    """
    with app.app_context():
        john = User(username='John')
        john.password_hash = 'Johnpassword1'

        jane = User(username='Jane')
        jane.password_hash = 'Janepassword1'

        db.session.add_all([john, jane])
        db.session.commit()

        return {
            'john': john.id,
            'jane': jane.id
        }


@pytest.fixture
def tasks(users):
    """
    Create six tasks for John and one private task for Jane.

    Returns task IDs for testing CRUD operations, pagination,
    and restrictions on accessing another user's tasks.
    """
    with app.app_context():
        records = [
            Task(
                title=f'John task {i}',
                description=f'Description {i}',
                status='pending',
                priority='low',
                user_id=users['john']
            )
            for i in range(1, 7)
        ]

        records.append(
            Task(
                title='Jane private task',
                status='pending',
                priority='high',
                user_id=users['jane']
            )
        )

        db.session.add_all(records)
        db.session.commit()

        return {
            'john': [task.id for task in records[:-1]],
            'jane': records[-1].id
        }


# --------------------------------------------------
# Test Helpers
# --------------------------------------------------

def login(client, username='John', password='Johnpassword1'):
    """
    Authenticate a test user through the login endpoint.

    Defaults to John's credentials but accepts overrides
    for testing other accounts or invalid credentials.
    """
    return client.post(
        '/login',
        json={
            'username': username,
            'password': password
        }
    )


def valid_task(**overrides):
    """
    Generate a valid task payload for API requests.

    Individual fields can be overridden to test
    validation errors or alternative task values.
    """
    payload = {
        'title': 'Write tests',
        'description': 'Cover the API',
        'status': 'pending',
        'priority': 'medium',
        'due_date': '2026-12-01'
    }

    payload.update(overrides)

    return payload


# --------------------------------------------------
# User Registration and Authentication
# --------------------------------------------------

def test_signup_creates_user_and_starts_session(client):
    """
    Verify that signup creates a user, excludes password hashes
    from the response, and establishes an authenticated session.
    """
    response = client.post(
        '/signup',
        json={
            'username': 'NewUser',
            'password': 'secret123',
            'password_confirmation': 'secret123'
        }
    )

    assert response.status_code == 201
    assert response.json['username'] == 'NewUser'
    assert '_password_hash' not in response.json
    assert client.get('/check_session').status_code == 200


@pytest.mark.parametrize('payload,status', [
    ({'username': '', 'password': 'secret'}, 422),
    ({'username': 'NewUser', 'password': ''}, 422),
    ([], 400),
])
def test_signup_rejects_invalid_input(client, payload, status):
    """
    Verify that signup rejects missing credentials
    and requests that do not contain a JSON object.
    """
    assert client.post(
        '/signup',
        json=payload
    ).status_code == status


def test_get_task_requires_authentication(client):
    """
    Verify that unauthenticated users cannot access
    individual tasks through the API.
    """
    response = client.get('/tasks/99999')

    assert response.status_code == 401


# --------------------------------------------------
# Task Updates and Deletion
# --------------------------------------------------

def test_patch_single_field(client, tasks):
    """Verify that PATCH can update an individual task field."""
    login(client)

    response = client.patch(
        f"/tasks/{tasks['john'][0]}",
        json={'title': 'Updated title'}
    )

    assert response.status_code == 200
    assert response.json['title'] == 'Updated title'


def test_patch_multiple_fields(client, tasks):
    """Verify that PATCH can update multiple task fields at once."""
    login(client)

    response = client.patch(
        f"/tasks/{tasks['john'][0]}",
        json={
            'title': 'Finished task',
            'status': 'completed',
            'priority': 'high',
            'due_date': '2026-12-15'
        }
    )

    assert response.status_code == 200
    assert response.json['status'] == 'completed'
    assert response.json['priority'] == 'high'
    assert response.json['due_date'] == '2026-12-15'


@pytest.mark.parametrize('payload,status', [
    ({'title': ''}, 422),
    ({'status': 'invalid'}, 422),
    ({'priority': 'urgent'}, 422),
    ({'due_date': 'tomorrow'}, 422),
    ([], 400),
])
def test_patch_rejects_invalid_input(client, tasks, payload, status):
    """
    Verify that task updates reject invalid field values
    and malformed JSON request bodies.
    """
    login(client)

    response = client.patch(
        f"/tasks/{tasks['john'][0]}",
        json=payload
    )

    assert response.status_code == status


def test_failed_patch_rolls_back_changes(client, tasks):
    """
    Verify that an invalid update does not persist partial changes.

    The request contains a valid title but an invalid status.
    The original title must remain unchanged after the error.
    """
    login(client)

    task_id = tasks['john'][0]

    response = client.patch(
        f'/tasks/{task_id}',
        json={
            'title': 'Should not persist',
            'status': 'invalid'
        }
    )

    assert response.status_code == 422
    assert client.get(
        f'/tasks/{task_id}'
    ).json['title'] == 'John task 1'


def test_patch_missing_task_returns_404(client, users):
    """Verify that updating a nonexistent task returns HTTP 404."""
    login(client)

    assert client.patch(
        '/tasks/99999',
        json={'title': 'X'}
    ).status_code == 404


def test_delete_task(client, tasks):
    """
    Verify that deleting an owned task returns HTTP 204
    and that the deleted task can no longer be retrieved.
    """
    login(client)

    task_id = tasks['john'][0]

    assert client.delete(f'/tasks/{task_id}').status_code == 204
    assert client.get(f'/tasks/{task_id}').status_code == 404


def test_delete_missing_task_returns_404(client, users):
    """Verify that deleting a nonexistent task returns HTTP 404."""
    login(client)

    assert client.delete('/tasks/99999').status_code == 404


# --------------------------------------------------
# Task Ownership and User Isolation
# --------------------------------------------------

@pytest.mark.parametrize('method,payload', [
    ('get', None),
    ('patch', {'title': 'Stolen'}),
    ('delete', None),
])
def test_cannot_access_another_users_task(
    client, tasks, method, payload
):
    """
    Verify that users cannot read, modify, or delete tasks
    belonging to another user.

    Unauthorized ownership access returns HTTP 404.
    The original task must remain unchanged.
    """
    login(client)

    path = f"/tasks/{tasks['jane']}"

    # Execute the requested HTTP method with a payload if provided
    response = (
        getattr(client, method)(path, json=payload)
        if payload is not None
        else getattr(client, method)(path)
    )

    assert response.status_code == 404

    # Confirm that Jane's task still exists and was not modified
    with app.app_context():
        assert (
            db.session.get(Task, tasks['jane']).title
            == 'Jane private task'
        )


# --------------------------------------------------
# Task Pagination
# --------------------------------------------------

def test_pagination_defaults(client, tasks):
    """
    Verify that pagination defaults to page 1
    with five tasks per page.
    """
    login(client)

    response = client.get('/tasks')

    assert response.status_code == 200
    assert response.json['page'] == 1
    assert response.json['per_page'] == 5
    assert response.json['total'] == 6
    assert response.json['total_pages'] == 2
    assert len(response.json['items']) == 5


def test_pagination_pages_do_not_overlap(client, tasks):
    """
    Verify that consecutive pages return distinct tasks
    while preserving the same total task count.
    """
    login(client)

    first = client.get('/tasks?page=1&per_page=2').json
    second = client.get('/tasks?page=2&per_page=2').json

    assert first['total'] == second['total'] == 6
    assert first['total_pages'] == second['total_pages'] == 3
    assert len(first['items']) == len(second['items']) == 2

    # Confirm that no task ID appears on both pages
    assert {t['id'] for t in first['items']}.isdisjoint(
        {t['id'] for t in second['items']}
    )


def test_pagination_out_of_range_returns_empty_items(client, tasks):
    """
    Verify that requesting a page beyond the available
    results returns an empty list rather than an error.
    """
    login(client)

    response = client.get('/tasks?page=4&per_page=2')

    assert response.status_code == 200
    assert response.json['items'] == []
    assert response.json['total'] == 6


@pytest.mark.parametrize('query', [
    'page=0',
    'page=-1',
    'per_page=0',
    'per_page=-5',
    'page=abc',
    'per_page=xyz',
    'page=',
    'per_page=',
])
def test_pagination_rejects_invalid_parameters(client, tasks, query):
    """
    Verify that pagination rejects zero, negative,
    nonnumeric, and empty query parameter values.
    """
    login(client)

    response = client.get(f'/tasks?{query}')

    assert response.status_code == 400
    assert (
        response.json['message']
        == 'Page and per_page must be positive integers'
    )