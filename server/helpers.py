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