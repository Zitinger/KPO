class Invoker:
    def __init__(self):
        self.history = []

    def run(self, command):
        result = command.execute()
        self.history.append(command)
        return result
