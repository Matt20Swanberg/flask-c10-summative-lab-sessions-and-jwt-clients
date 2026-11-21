"""
Seed the database with sample users and tasks

Creates three development users with hashed passwords and ensures
each user has five tasks with randomized statuses and priorities

The script can be rerun without duplicating existing users or
adding tasks beyond the five-task target
"""

from faker import Faker

from server.config import app, db
from server.models import User, Task


# Initialize Faker to generate sample task content
fake = Faker()

# Define development users and valid task field values
USERNAMES = ['John', 'Jane', 'Bob']
STATUS_OPTIONS = ['pending', 'in_progress', 'completed']
PRIORITY_OPTIONS = ['low', 'medium', 'high']

# Number of tasks to create for each development user
TASKS_PER_USER = 5


with app.app_context():

    # --------------------------------------------------
    # Seed Users
    # --------------------------------------------------

    print("Creating users...")


    for username in USERNAMES:

        # Skip users that already exist to prevent duplicates
        if not User.query.filter_by(username=username).first():
            user = User(username=username)

            # Hash the development password using the model's setter
            user.password_hash = user.username + 'password1'

            db.session.add(user)

    # Save all newly created users in a single transaction
    db.session.commit()

    # --------------------------------------------------
    # Seed Tasks
    # --------------------------------------------------

    print("Creating tasks...")

    # Retrieve only the designated development users
    users = User.query.filter(User.username.in_(USERNAMES)).all()

    for user in users:

        # Add tasks until the user has five total
        while len(user.tasks) < TASKS_PER_USER:
            task = Task(
                title=fake.sentence(nb_words=5),
                description=fake.paragraph(nb_sentences=2),
                status=fake.random_element(elements=STATUS_OPTIONS),
                priority=fake.random_element(elements=PRIORITY_OPTIONS),
            )

            # Associate the task with its owner
            task.user = user

            # Stage the task for insertion
            db.session.add(task)

    # Save all newly created tasks
    db.session.commit()

    # --------------------------------------------------
    # Verify Seed Results
    # --------------------------------------------------

    print(f"Total users in database: {User.query.count()}")
    print(f"Total tasks in database: {Task.query.count()}")
    print("Database seeding complete!")