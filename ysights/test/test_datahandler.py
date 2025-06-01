import unittest
import os
import networkx as nx
from ysights.models.YDataHandler import YDataHandler, Agents, Agent, Posts, Post


class DataHandlerTestCase(unittest.TestCase):
    @staticmethod
    def get_data_handler():
        # Assuming the database file exists at this path
        db_path = f"{os.sep}example_data{os.sep}ysocial_db.db"

        current_path = os.getcwd().split("ysights")[0] + "ysights" + db_path

        handler = YDataHandler(current_path)
        return handler

    def test_get_agents(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        # Fetch agents
        agents = handler.agents()

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
        num_agents = handler.number_of_agents()

        # Check if the number of agents is an integer
        self.assertIsInstance(num_agents, int)

        # Close the database connection
        handler.close()

    def test_get_agents_by_feature(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        agents = handler.agents_by_feature("age", 25)
        # Check if agents is a list
        self.assertIsInstance(agents, Agents)
        # Check if each agent is a dictionary with expected keys
        for agent in agents.get_agents():
            self.assertIsInstance(agent, Agent)
        # Close the database connection
        handler.close()

    def test_agent_recommendations(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        recommendations = handler.agent_recommendations(99)
        # Check if recommendations is a list
        self.assertIsInstance(recommendations, dict)
        # Check if each recommendation is a dictionary with expected keys
        for rec, count in recommendations.items():
            self.assertIsInstance(rec, tuple)
            self.assertIsInstance(count, int)
        # Close the database connection
        handler.close()

    def test_get_posts_by_agent(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        posts = handler.posts_by_agent(99, enrich_dimensions=["all"])
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

        interest_profile = handler.agent_interests(agent_id)

        # Check if interest profile is a dictionary
        self.assertIsInstance(interest_profile, dict)
        handler.close()

    def test_ego_network(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        ego_network_follower = handler.ego_network_follower(99)
        self.assertIsInstance(ego_network_follower, nx.DiGraph)

        ego_network_following = handler.ego_network_following(99)
        self.assertIsInstance(ego_network_following, nx.DiGraph)

        ego_network = handler.ego_network(99)
        self.assertIsInstance(ego_network, nx.DiGraph)

        handler.close()

    def test_network(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        network = handler.social_network()
        self.assertIsInstance(network, nx.DiGraph)

        handler.close()

    def test_agent_mapping(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        agent_mapping = handler.agent_mapping()
        self.assertIsInstance(agent_mapping, dict)
        for key, value in agent_mapping.items():
            self.assertIsInstance(key, int)
            self.assertIsInstance(value, str)

        handler.close()

    def test_agent_reactions(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        reactions = handler.agent_reactions(99)
        self.assertIsInstance(reactions, dict)
        for key, value in reactions.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, list)

        handler.close()

    def test_agent_hashtags(self):
        handler = self.get_data_handler()
        handler.connect()
        hashtags = handler.agent_hashtags(99)
        self.assertIsInstance(hashtags, dict)
        for hashtag in hashtags:
            self.assertIsInstance(hashtag, str)
        handler.close()

    def test_agent_emotions(self):
        handler = self.get_data_handler()
        handler.connect()
        emotions = handler.agent_emotions(99)
        self.assertIsInstance(emotions, dict)
        for emotion in emotions:
            self.assertIsInstance(emotion, str)
        handler.close()

    def test_mention_network(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        mention_network = handler.mention_network()
        self.assertIsInstance(mention_network, nx.DiGraph)

        handler.close()

    def test_toxicity(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        toxicity = handler.agent_toxicity(99)
        self.assertIsInstance(toxicity, list)

        for item in toxicity:
            for key, value in item.items():
                self.assertIsInstance(key, str)
                self.assertIsInstance(value, float)

        handler.close()

    def test_time(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        time = handler.time_range()
        self.assertIsInstance(time, dict)
        for key, value in time.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, int)

        handler.close()

    def test_round_to_time(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        round_time = handler.round_to_time(20)
        self.assertIsInstance(round_time, dict)
        for key, value in round_time.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, int)

        handler.close()

    def test_time_to_round(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        time_round = handler.time_to_round(10, 10)
        self.assertIsInstance(time_round, int)

        handler.close()

    def test_agent_posts_visibility(self):
        handler = self.get_data_handler()
        # Connect to the database
        handler.connect()

        rec_stats = handler.recommendations_per_post()
        visibility = handler.agent_posts_visibility(99, rec_stats)
        self.assertIsInstance(visibility, dict)
        for key, value in visibility.items():
            self.assertIsInstance(key, int)
            self.assertIsInstance(value, int)

        handler.close()


if __name__ == "__main__":
    unittest.main()
