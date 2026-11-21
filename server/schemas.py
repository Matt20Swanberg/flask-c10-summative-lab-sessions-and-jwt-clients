from marshmallow import Schema, fields


class UserSchema(Schema):
    """
    Defines how User model instances are serialized into JSON

    Exposes the user's ID and username while excluding
    sensitive information such as the stored password hash
    """

    id = fields.Int()
    username = fields.Str()


class TaskSchema(Schema):
    """
    Defines how Task model instances are serialized into JSON

    Includes task details, workflow status, priority, optional
    due date, and the ID of the user who owns the task

    The due_date field uses Marshmallow's Date field to
    serialize Python date objects as ISO-formatted strings
    """

    # Task identification and details
    id = fields.Int()
    title = fields.Str()
    description = fields.Str()

    # Workflow and scheduling information
    status = fields.Str()
    priority = fields.Str()
    due_date = fields.Date()

    # Reference to the user who owns the task
    user_id = fields.Int()