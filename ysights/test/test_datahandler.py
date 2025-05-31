import unittest
import os
from ysights.models.DataHandler import DataHandler, Agents, Agent, Posts, Post


class DataHandlerTestCase(unittest.TestCase):
    @staticmethod
    def get_data_handler():
        # Assuming the database file exists at this path
        db_path = f"{os.sep}example_data{os.sep}ysocial_db.db"

        current_path = os.getcwd().split("ysights")[0] + "ysights" + db_path

        handler = DataHandler(current_path)
        return handler

    def test_get_agents(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        # Fetch agents
        agents = handler.get_agents()

        # Check if agents is a list
        self.assertIsInstance(agents, Agents)

        # Check if each agent is a dictionary with expected keys
        for agent in agents.get_agents():
            self.assertIsInstance(agent, Agent)

        # Close the database connection
        handler.close()

    def test_get_number_of_agents(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        # Fetch number of agents
        num_agents = handler.get_number_of_agents()

        # Check if the number of agents is an integer
        self.assertIsInstance(num_agents, int)

        # Close the database connection
        handler.close()

    def test_get_agents_by_feature(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        agents = handler.get_agents_by_feature("age", 25)
        # Check if agents is a list
        self.assertIsInstance(agents, Agents)
        # Check if each agent is a dictionary with expected keys
        for agent in agents.get_agents():
            self.assertIsInstance(agent, Agent)
        # Close the database connection
        handler.close()

    def test_get_posts_by_agent(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        posts = handler.get_posts_by_agent(99, enrich_dimensions=["all"])
        # Check if posts is a list
        self.assertIsInstance(posts, Posts)
        # Check if each post is a dictionary with expected keys
        for post in posts.get_posts():
            self.assertIsInstance(post, Post)

        # Close the database connection
        handler.close()

    def test_get_agent_interest_profile(self, agent_id=99):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        interest_profile = handler.get_agent_interest_profile(agent_id)

        # Check if interest profile is a dictionary
        self.assertIsInstance(interest_profile, dict)

        print(interest_profile)
        handler.close()


if __name__ == "__main__":
    unittest.main()
