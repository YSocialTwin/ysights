import json


class Agent:
    """
    A class to represent an agent.
    This class is used to define the properties and behaviors of an agent.
    """

    def __init__(self, row):
        self.id = row[0]
        self.username = row[1]
        self.role = row[4]
        self.leaning = row[5]
        self.age = row[6]
        self.personality = {
            "oe": row[7],
            "co": row[8],
            "ex": row[9],
            "ag": row[10],
            "ne": row[11],
        }
        self.recsys = {
            "content": row[12],
            "social": row[17],
        }
        self.language = row[13]
        self.education = row[15]
        self.joined = row[16]
        self.gender = row[18]
        self.nationality = row[19]
        self.toxicity = row[20]
        self.is_page = row[21]
        self.left_on = row[22]
        self.daily_activity_level = row[23]
        self.profession = row[24]

    def __repr__(self):
        return f"Agent(id={self.id}, username={self.username}, role={self.role}, leaning={self.leaning}, age={self.age}, personality={self.personality}, recsys={self.recsys}, language={self.language}, education={self.education}, joined={self.joined}, gender={self.gender})"

    def __str__(self):
        json.dumps(
            {
                "id": self.id,
                "username": self.username,
                "role": self.role,
                "leaning": self.leaning,
                "age": self.age,
                "personality": self.personality,
                "recsys": self.recsys,
                "language": self.language,
                "education": self.education,
                "joined": self.joined,
                "gender": self.gender,
                "nationality": self.nationality,
                "is_page": self.is_page,
                "toxicity": self.toxicity,
                "left_on": self.left_on,
                "daily_activity_level": self.daily_activity_level,
                "profession": self.profession,
            }
        )


class Agents:
    """
    A class to represent a collection of agents.
    This class is used to manage and interact with multiple agents.
    """

    def __init__(self):
        self.agents = []

    def add_agent(self, agent):
        """Add an agent to the collection."""
        self.agents.append(agent)

    def get_agents(self):
        """Return the list of agents."""
        return self.agents

    def __repr__(self):
        return f"Agents({self.agents})"
