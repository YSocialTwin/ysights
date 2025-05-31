import sqlite3
import os
from collections import defaultdict

from ysights.models.Agents import Agents, Agent
from ysights.models.Posts import Posts, Post


class DataHandler:
    def __init__(self, db_path):
        """
        Initialize the DataHandler with the path to the SQLite database.
        :param db_path:
        """
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """
        Connect to the SQLite database.
        :return:
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file {self.db_path} does not exist.")
        self.connection = sqlite3.connect(self.db_path)

    def close(self):
        """
        Close the database connection if it is open.
        :return:
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_cursor(self):
        """
        Get a cursor for executing SQL queries.
        :return:
        """
        if not self.connection:
            raise FileNotFoundError("Database connection is not established.")
        return self.connection.cursor()

    def __execute_query(self, query, params=None):
        """
        Execute a SQL query and return the results.
        :param query:
        :param params:
        :return:
        """
        if not self.connection:
            raise FileNotFoundError("Database connection is not established.")
        cursor = self.connection.cursor()
        cursor.execute(query, params or [])
        return cursor.fetchall()

    def get_agents(self):
        """
        Retrieve all agents from the database.
        :return:
        """
        query = "SELECT * FROM user_mgmt"
        data = self.__execute_query(query)
        agents = Agents()
        for row in data:
            ag = Agent(row)
            agents.add_agent(ag)
        return agents

    def get_number_of_agents(self):
        """
        Retrieve the number of agents in the database.
        :return:
        """
        query = "SELECT COUNT(*) FROM user_mgmt"
        data = self.__execute_query(query)
        return data[0][0] if data else 0

    def get_agents_by_feature(self, feature, value):
        """
        Retrieve agents based on a specific feature and value.
        :param feature:
        :param value:
        :return:
        """
        query = f"SELECT * FROM user_mgmt WHERE {feature} = ?"
        data = self.__execute_query(query, (value,))
        agents = Agents()
        for row in data:
            ag = Agent(row)
            agents.add_agent(ag)
        return agents

    def get_posts_by_agent(
        self, agent_id, enrich_dimensions: list = ["sentiment", "hashtags"]
    ):
        """
        Retrieve posts made by a specific agent.
        :param agent_id:
        :param enrich_dimensions:
        :return:
        """
        query = "SELECT * FROM post WHERE user_id = ?"
        data = self.__execute_query(query, (agent_id,))
        posts = Posts()
        for row in data:
            post = Post(row)
            if len(enrich_dimensions) > 0:
                # Enrich the post with additional data
                post.enrich_post(self.get_cursor(), enrich_dimensions)
            posts.add_post(post)
        return posts

    def get_agent_interest_profile(self, agent_id, from_round=None, to_round=None):
        """
        Retrieve the interest profile of a specific agent.
        :param agent_id:
        :param from_round:
        :param to_round:
        :return:
        """

        if from_round is not None and to_round is not None:
            query = "SELECT i.interest FROM user_interest as ui, interests as i WHERE user_id = ? AND i.iid = ui.interest_id AND ui.round >= ? AND ui.round <= ?"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT i.interest FROM user_interest as ui, interests as i WHERE user_id = ? AND i.iid = ui.interest_id"
            data = self.__execute_query(query, (agent_id,))

        interests = defaultdict(int)
        for row in data:
            interests[row[0]] += 1

        return interests
