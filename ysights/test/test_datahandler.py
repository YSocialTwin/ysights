import os
import unittest

import networkx as nx

from ysights.models.YDataHandler import Agent, Agents, Post, Posts, YDataHandler


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

        # Fetch agents
        agents = handler.agents()

        # Check if agents is a list
        self.assertIsInstance(agents, Agents)

        # Check if each agent is a dictionary with expected keys
        for agent in agents.get_agents():
            self.assertIsInstance(agent, Agent)

    def test_get_number_of_agents(self):
        handler = self.get_data_handler()

        # Fetch number of agents
        num_agents = handler.number_of_agents()

        # Check if the number of agents is an integer
        self.assertIsInstance(num_agents, int)

    def test_get_agents_by_feature(self):
        handler = self.get_data_handler()

        agents = handler.agents_by_feature("age", 25)
        # Check if agents is a list
        self.assertIsInstance(agents, Agents)
        # Check if each agent is a dictionary with expected keys
        for agent in agents.get_agents():
            self.assertIsInstance(agent, Agent)

    def test_agent_recommendations(self):
        handler = self.get_data_handler()

        recommendations = handler.agent_recommendations(99)
        # Check if recommendations is a list
        self.assertIsInstance(recommendations, dict)
        # Check if each recommendation is a dictionary with expected keys
        for rec, count in recommendations.items():
            self.assertIsInstance(rec, tuple)
            self.assertIsInstance(count, int)

    def test_get_posts_by_agent(self):
        handler = self.get_data_handler()

        posts = handler.posts_by_agent(99, enrich_dimensions=["all"])
        # Check if posts is a list
        self.assertIsInstance(posts, Posts)
        # Check if each post is a dictionary with expected keys
        for post in posts.get_posts():
            self.assertIsInstance(post, Post)

    def test_get_agent_interest_profile(self, agent_id=99):
        handler = self.get_data_handler()

        interest_profile = handler.agent_interests(agent_id)

        # Check if interest profile is a dictionary
        self.assertIsInstance(interest_profile, dict)

    def test_ego_network(self):
        handler = self.get_data_handler()

        ego_network_follower = handler.ego_network_follower(99)
        self.assertIsInstance(ego_network_follower, nx.DiGraph)

        ego_network_following = handler.ego_network_following(99)
        self.assertIsInstance(ego_network_following, nx.DiGraph)

        ego_network = handler.ego_network(99)
        self.assertIsInstance(ego_network, nx.DiGraph)

    def test_network(self):
        handler = self.get_data_handler()

        network = handler.social_network()
        self.assertIsInstance(network, nx.DiGraph)

    def test_agent_mapping(self):
        handler = self.get_data_handler()

        agent_mapping = handler.agent_mapping()
        self.assertIsInstance(agent_mapping, dict)
        for key, value in agent_mapping.items():
            self.assertIsInstance(key, int)
            self.assertIsInstance(value, str)

    def test_agent_reactions(self):
        handler = self.get_data_handler()

        reactions = handler.agent_reactions(99)
        self.assertIsInstance(reactions, dict)
        for key, value in reactions.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, list)

    def test_agent_hashtags(self):
        handler = self.get_data_handler()
        hashtags = handler.agent_hashtags(99)
        self.assertIsInstance(hashtags, dict)
        for hashtag in hashtags:
            self.assertIsInstance(hashtag, str)

    def test_agent_emotions(self):
        handler = self.get_data_handler()
        emotions = handler.agent_emotions(99)
        self.assertIsInstance(emotions, dict)
        for emotion in emotions:
            self.assertIsInstance(emotion, str)

    def test_mention_network(self):
        handler = self.get_data_handler()

        mention_network = handler.mention_network()
        self.assertIsInstance(mention_network, nx.DiGraph)

    def test_toxicity(self):
        handler = self.get_data_handler()

        toxicity = handler.agent_toxicity(99)
        self.assertIsInstance(toxicity, list)

        for item in toxicity:
            for key, value in item.items():
                self.assertIsInstance(key, str)
                self.assertIsInstance(value, float)

    def test_time(self):
        handler = self.get_data_handler()

        time = handler.time_range()
        self.assertIsInstance(time, dict)
        for key, value in time.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, int)

    def test_round_to_time(self):
        handler = self.get_data_handler()

        round_time = handler.round_to_time(20)
        self.assertIsInstance(round_time, dict)
        for key, value in round_time.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, int)

    def test_time_to_round(self):
        handler = self.get_data_handler()

        time_round = handler.time_to_round(10, 10)
        self.assertIsInstance(time_round, int)

    def test_agent_posts_visibility(self):
        handler = self.get_data_handler()

        rec_stats = handler.recommendations_per_post()
        visibility = handler.agent_posts_visibility(99, rec_stats)
        self.assertIsInstance(visibility, dict)
        for key, value in visibility.items():
            self.assertIsInstance(key, int)
            self.assertIsInstance(value, int)

    def test_custom_query(self):
        handler = self.get_data_handler()

        query = "SELECT * FROM user_mgmt WHERE id = 1"
        result = handler.custom_query(query)

        # Check if result is a list
        self.assertIsInstance(result, list)

        # Check if each item in the result is a dictionary
        for item in result:
            self.assertIsInstance(item, tuple)


if __name__ == "__main__":
    unittest.main()
