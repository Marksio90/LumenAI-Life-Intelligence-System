class GlobalState:
    def __init__(self):
        self.events = []

    def add_event(self, event: dict):
        self.events.append(event)

    def export(self):
        return {"events": self.events}
