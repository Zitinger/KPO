import uuid


class IdGenerator:
    def new_id(self):
        return str(uuid.uuid4())
