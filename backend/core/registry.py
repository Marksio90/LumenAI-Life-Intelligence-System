class AgentRegistry:
    def __init__(self):
        self.agents = {}

    def register(self, name: str, agent):
        self.agents[name] = agent

    def list(self):
        return list(self.agents.keys())

    def get(self, name: str):
        return self.agents.get(name)
