import os

os.environ.setdefault('SECRET_KEY', 'pytest-only-secret-key')

import pytest
from server.app import app
from server.config import app, db
from server.models import User, Task
from sqlalchemy import create_engine


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, SECRET_KEY='pytest-only-secret-key')
    test_engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    with app.app_context():
        original_engine = db.engines[None]
        db.session.remove()
        db.engines[None] = test_engine
        try:
            db.create_all()
            with app.test_client() as test_client:
                yield test_client
        finally:
            db.session.remove()
            db.drop_all()
            db.engines[None] = original_engine
            test_engine.dispose()


@pytest.fixture
def users(client):
    with app.app_context():
        john = User(username='John')
        john.password_hash = 'Johnpassword1'
        jane = User(username='Jane')
        jane.password_hash = 'Janepassword1'
        db.session.add_all([john, jane])
        db.session.commit()
        return {'john': john.id, 'jane': jane.id}


@pytest.fixture
def tasks(users):
    with app.app_context():
        records = [
            Task(title=f'John task {i}', description=f'Description {i}',
                 status='pending', priority='low', user_id=users['john'])
            for i in range(1, 7)
        ]
        records.append(Task(title='Jane private task', status='pending',
                            priority='high', user_id=users['jane']))
        db.session.add_all(records)
        db.session.commit()
        return {'john': [task.id for task in records[:-1]],
                'jane': records[-1].id}


def login(client, username='John', password='Johnpassword1'):
    return client.post('/login', json={'username': username, 'password': password})


def valid_task(**overrides):
    payload = {'title': 'Write tests', 'description': 'Cover the API',
               'status': 'pending', 'priority': 'medium', 'due_date': '2026-12-01'}
    payload.update(overrides)
    return payload


def test_signup_creates_user_and_starts_session(client):
    response = client.post('/signup', json={'username': 'NewUser', 'password': 'secret123'})
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
    assert client.post('/signup', json=payload).status_code == status


    login(client)
    assert client.get('/tasks/99999').status_code == 401


# Updates and deletion

def test_patch_single_field(client, tasks):
    login(client)
    response = client.patch(f"/tasks/{tasks['john'][0]}", json={'title': 'Updated title'})
    assert response.status_code == 200
    assert response.json['title'] == 'Updated title'


def test_patch_multiple_fields(client, tasks):
    login(client)
    response = client.patch(f"/tasks/{tasks['john'][0]}", json={
        'title': 'Finished task', 'status': 'completed', 'priority': 'high',
        'due_date': '2026-12-15',
    })
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
    login(client)
    response = client.patch(f"/tasks/{tasks['john'][0]}", json=payload)
    assert response.status_code == status


def test_failed_patch_rolls_back_changes(client, tasks):
    login(client)
    task_id = tasks['john'][0]
    response = client.patch(f'/tasks/{task_id}', json={
        'title': 'Should not persist', 'status': 'invalid',
    })
    assert response.status_code == 422
    assert client.get(f'/tasks/{task_id}').json['title'] == 'John task 1'


def test_patch_missing_task_returns_404(client, users):
    login(client)
    assert client.patch('/tasks/99999', json={'title': 'X'}).status_code == 404


def test_delete_task(client, tasks):
    login(client)
    task_id = tasks['john'][0]
    assert client.delete(f'/tasks/{task_id}').status_code == 204
    assert client.get(f'/tasks/{task_id}').status_code == 404


def test_delete_missing_task_returns_404(client, users):
    login(client)
    assert client.delete('/tasks/99999').status_code == 404


@pytest.mark.parametrize('method,payload', [
    ('get', None),
    ('patch', {'title': 'Stolen'}),
    ('delete', None),
])
def test_cannot_access_another_users_task(client, tasks, method, payload):
    login(client)
    path = f"/tasks/{tasks['jane']}"
    response = getattr(client, method)(path, json=payload) if payload is not None else getattr(client, method)(path)
    assert response.status_code == 404
    with app.app_context():
        assert db.session.get(Task, tasks['jane']).title == 'Jane private task'


# Pagination

def test_pagination_defaults(client, tasks):
    login(client)
    response = client.get('/tasks')
    assert response.status_code == 200
    assert response.json['page'] == 1
    assert response.json['per_page'] == 5
    assert response.json['total'] == 6
    assert response.json['total_pages'] == 2
    assert len(response.json['items']) == 5


def test_pagination_pages_do_not_overlap(client, tasks):
    login(client)
    first = client.get('/tasks?page=1&per_page=2').json
    second = client.get('/tasks?page=2&per_page=2').json
    assert first['total'] == second['total'] == 6
    assert first['total_pages'] == second['total_pages'] == 3
    assert len(first['items']) == len(second['items']) == 2
    assert {t['id'] for t in first['items']}.isdisjoint({t['id'] for t in second['items']})


def test_pagination_out_of_range_returns_empty_items(client, tasks):
    login(client)
    response = client.get('/tasks?page=4&per_page=2')
    assert response.status_code == 200
    assert response.json['items'] == []
    assert response.json['total'] == 6


@pytest.mark.parametrize('query', [
    'page=0', 'page=-1', 'per_page=0', 'per_page=-5',
    'page=abc', 'per_page=xyz', 'page=', 'per_page=',
])
def test_pagination_rejects_invalid_parameters(client, tasks, query):
    login(client)
    response = client.get(f'/tasks?{query}')
    assert response.status_code == 400
    assert response.json['message'] == 'Page and per_page must be positive integers'
