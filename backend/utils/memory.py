class MemoryManager:
    def __init__(self):
        self.short_term = []
        self.long_term = []

    def add(self, memory: dict):
        self.short_term.append(memory)

    def flush_to_long_term(self):
        self.long_term.extend(self.short_term)
        self.short_term = []
