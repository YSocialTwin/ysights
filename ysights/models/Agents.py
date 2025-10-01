import json


class Agent:
    """
    Represents a social media agent in the YSocial simulation.

    This class encapsulates all properties and characteristics of an agent, including
    demographic information, personality traits, recommendation system preferences,
    and behavioral attributes.

    :param row: A database row tuple containing agent data in a specific order:
                [id, username, ?, ?, role, leaning, age, oe, co, ex, ag, ne,
                content_recsys, language, ?, education, joined, social_recsys,
                gender, nationality, toxicity, is_page, left_on, daily_activity_level, profession]
    :type row: tuple

    :ivar int id: Unique identifier for the agent
    :ivar str username: The agent's username
    :ivar str role: The agent's role in the simulation
    :ivar str leaning: Political or ideological leaning of the agent
    :ivar int age: Age of the agent
    :ivar dict personality: Big Five personality traits (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism)
    :ivar dict recsys: Recommendation system preferences (content-based and social-based weights)
    :ivar str language: Primary language of the agent
    :ivar str education: Education level of the agent
    :ivar int joined: Round/time when the agent joined the simulation
    :ivar str gender: Gender of the agent
    :ivar str nationality: Nationality of the agent
    :ivar float toxicity: Toxicity level of the agent's behavior
    :ivar bool is_page: Whether the agent is a page (organizational account) or individual
    :ivar int left_on: Round/time when the agent left the simulation (if applicable)
    :ivar float daily_activity_level: Activity level of the agent per day
    :ivar str profession: Professional occupation of the agent

    Example:
        Creating an agent from a database row::

            from ysights.models.Agents import Agent

            # Example database row
            row = (1, 'alice_smith', None, None, 'user', 'moderate', 32,
                   0.7, 0.6, 0.8, 0.5, 0.4, 0.5, 'en', None, 'college',
                   0, 0.5, 'female', 'USA', 0.1, False, None, 3.5, 'teacher')

            agent = Agent(row)
            print(f"Agent ID: {agent.id}")
            print(f"Username: {agent.username}")
            print(f"Personality: {agent.personality}")
            print(f"Age: {agent.age}, Gender: {agent.gender}")

    See Also:
        :class:`Agents`: Collection class for managing multiple agents
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
    A container class for managing a collection of Agent objects.

    This class provides methods to add agents to the collection and retrieve
    the list of agents. It serves as a convenient way to group and manipulate
    multiple agents from a YSocial simulation.

    :ivar list agents: Internal list storing all Agent objects

    Example:
        Managing a collection of agents::

            from ysights import YDataHandler
            from ysights.models.Agents import Agents, Agent

            # Create an agents collection
            agents = Agents()

            # Add agents to the collection
            row1 = (1, 'alice', None, None, 'user', 'left', 25, 0.7, 0.6, 0.8, 0.5, 0.4,
                    0.5, 'en', None, 'college', 0, 0.5, 'female', 'USA', 0.1, False,
                    None, 3.5, 'teacher')
            agent1 = Agent(row1)
            agents.add_agent(agent1)

            # Or retrieve from database
            ydh = YDataHandler('path/to/database.db')
            all_agents = ydh.agents()

            # Get list of all agents
            agent_list = all_agents.get_agents()
            print(f"Total agents: {len(agent_list)}")

            # Iterate through agents
            for agent in agent_list:
                print(f"{agent.username}: {agent.role}")

    See Also:
        :class:`Agent`: Individual agent class
        :meth:`ysights.models.YDataHandler.YDataHandler.agents`: Retrieve agents from database
    """

    def __init__(self):
        """
        Initialize an empty Agents collection.
        """
        self.agents = []

    def add_agent(self, agent):
        """
        Add an agent to the collection.

        :param agent: The Agent object to add to the collection
        :type agent: Agent

        Example::

            agents = Agents()
            agent = Agent(row_data)
            agents.add_agent(agent)
        """
        self.agents.append(agent)

    def get_agents(self):
        """
        Retrieve the list of all agents in the collection.

        :return: List of all Agent objects in this collection
        :rtype: list[Agent]

        Example::

            agents = Agents()
            # ... add agents ...
            agent_list = agents.get_agents()
            for agent in agent_list:
                print(agent.username)
        """
        return self.agents

    def __repr__(self):
        return f"Agents({self.agents})"
