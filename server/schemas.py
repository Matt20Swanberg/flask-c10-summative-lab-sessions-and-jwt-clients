from marshmallow import Schema, fields

class UserSchema(Schema):
    id = fields.Int()
    username = fields.Str()

class TaskSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    status = fields.Str()
    priority = fields.Str()
    due_date = fields.Date()
    user_id = fields.Int()
    