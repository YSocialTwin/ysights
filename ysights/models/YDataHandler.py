import sqlite3
import os
from collections import defaultdict, namedtuple

import networkx as nx

from ysights.models.Agents import Agents, Agent
from ysights.models.Posts import Posts, Post

UserPost = namedtuple("UserPost", ["agent_id", "post_id"])


class YDataHandler:
    def __init__(self, db_path):
        """
        Initialize the DataHandler with the path to the SQLite database.
        :param db_path:
        """
        self.db_path = db_path
        self.connection = None

    # Connection handling methods

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

    # Time

    def time_range(self):
        """
        Retrieve the range of rounds in the database.
        :return: (min_round, max_round)
        """
        query = "SELECT MIN(id), MAX(id) FROM rounds"
        data = self.__execute_query(query)
        if data and data[0]:
            return {"min_round": data[0][0], "max_round": data[0][1]}
        else:
            raise ValueError("No rounds found in the database.")

    def round_to_time(self, round_id):
        """
        Convert a round ID to a time representation.
        :param round_id:
        :return: (day, hour)
        """
        query = "SELECT day, hour FROM rounds WHERE id = ?"
        data = self.__execute_query(query, (round_id,))
        if data:
            return {"day": data[0][0], "hour": data[0][1]}
        else:
            raise ValueError(f"Round ID {round_id} does not exist in the database.")

    def time_to_round(self, day, hour=0):
        """
        Convert a time representation to a round ID.
        :param day:
        :param hour:
        :return: round_id
        """
        query = "SELECT id FROM rounds WHERE day = ? AND hour = ?"
        data = self.__execute_query(query, (day, hour))
        if data:
            return data[0][0]
        else:
            raise ValueError(f"No round found for day {day} and hour {hour}.")

    # Agents and Posts methods

    def number_of_agents(self):
        """
        Retrieve the number of agents in the database.
        :return:
        """
        query = "SELECT COUNT(*) FROM user_mgmt"
        data = self.__execute_query(query)
        return data[0][0] if data else 0

    def agents(self):
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

    def agents_by_feature(self, feature, value):
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

    def agent_mapping(self):
        """
        Retrieve a mapping of agent IDs to their usernames.
        :return:
        """
        query = "SELECT id, username FROM user_mgmt"
        data = self.__execute_query(query)
        agent_mapping = {}
        for row in data:
            agent_mapping[row[0]] = row[1]
        return agent_mapping

    def agent_post_ids(self, agent_id):
        """
        Retrieve all posts made by a specific agent.
        :param agent_id:
        :return:
        """
        query = "SELECT id FROM post WHERE user_id = ?"
        data = self.__execute_query(query, (agent_id,))
        posts = {}
        for row in data:
            post_id = row[0]
            posts[post_id] = post_id
        return posts

    def posts(self):
        """
        Retrieve all posts from the database.
        :return: Posts object containing all posts
        """
        query = "SELECT * FROM post"
        data = self.__execute_query(query)
        posts = Posts()
        for row in data:
            post = Post(row)
            posts.add_post(post)
        return posts

    def posts_by_agent(
        self, agent_id, enrich_dimensions: list = ["all"]
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

    def agent_id_by_post_id(self, post_id):
        """
        Retrieve the agent ID for a specific post ID.
        :param post_id:
        :return: agent_id
        """
        query = "SELECT user_id FROM post WHERE id = ?"
        data = self.__execute_query(query, (post_id,))
        if data:
            return data[0][0]
        else:
            raise ValueError(f"Post ID {post_id} does not exist in the database.")

    # Recommendations and visibility methods

    def agent_recommendations(self, agent_id, from_round=None, to_round=None):
        """
        Retrieve the recommendations received by a specific agent.
        :param agent_id:
        :param from_round:
        :param to_round:
        :return: Dictionary of UserPost (post author, id post) with the recommendation counter
        """
        if from_round is not None and to_round is not None:
            query = "SELECT r.post_ids FROM recommendations as r WHERE user_id = ? AND r.round >= ? AND r.round <= ?"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT r.post_ids FROM recommendations as r WHERE user_id = ?"
            data = self.__execute_query(query, (agent_id,))

        recommendations = defaultdict(int)
        for row in data:
            rw = row[0].split("|")

            for r in rw:
                aid = self.agent_id_by_post_id(int(r))
                recommendations[UserPost(agent_id=aid, post_id=int(r))] += 1

        return recommendations

    def agent_posts_visibility(self, agent_id, rec_stats, from_round=None, to_round=None):
        """
        Retrieve the visibility of posts made by a specific agent.
        :param agent_id:
        :param rec_stats: Dictionary of post IDs and their recommendation counts
        :param from_round:
        :param to_round:
        :return: Dictionary of post-IDs and their visibility (number of times they were recommended)
        """
        if from_round is not None and to_round is not None:
            query = "SELECT p.id FROM post as p WHERE p.user_id = ? AND p.id round >= ? AND round <= ?"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT p.id FROM post as p WHERE p.user_id = ?"
            data = self.__execute_query(query, (agent_id,))

        posts = {int(row[0]): None for row in data}
        # filter rec_stats to only include posts made by the agent
        filtered_recs = {k: v for k, v in rec_stats.items() if k in posts}
        return filtered_recs

    def recommendations_per_post(self):
        """
        Retrieve the number of recommendations per post.
        :return: Dictionary of post-IDs and their recommendation counts
        """

        # get all recommendations
        query = "SELECT r.post_ids FROM recommendations as r"
        recs = self.__execute_query(query)

        rec_stats = defaultdict(int)
        for row in recs:
            rw = row[0].split("|")
            for r in rw:
                rec_stats[int(r)] += 1

        return rec_stats

    def recommendations_per_post_per_user(self):
        """
        Retrieve the number of recommendations per post per user.
        :return: Dictionary of UserPost (post author, id post) with the recommendation counter
        """

        # get all recommendations
        query = "SELECT r.user_id, r.post_ids FROM recommendations as r"
        recs = self.__execute_query(query)

        post_recs = {}
        user_to_posts_read = defaultdict(list)
        for uid, pts in recs:

            pt_ids = pts.split("|")
            for p in pt_ids:
                user_to_posts_read[uid].append(int(p))
                if p not in post_recs:
                    post_recs[int(p)] = 1

                else:
                    post_recs[int(p)] += 1

        return post_recs, user_to_posts_read

    # Agent profiles

    def agent_reactions(self, agent_id, from_round=None, to_round=None):
        """
        Retrieve all posts reacted to by a specific agent.
        :param agent_id:
        :param from_round:
        :param to_round:
        :return:
        """
        if from_round is not None and to_round is not None:
            query = "SELECT post_id, type FROM reactions WHERE user_id = ? AND round >= ? AND round <= ?"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT post_id, type FROM reactions WHERE user_id = ?"
            data = self.__execute_query(query, (agent_id,))

        reactions = defaultdict(list)
        for row in data:
            reactions[row[1]].append(row[0])

        return reactions

    def agent_hashtags(self, agent_id, from_round=None, to_round=None):
        """
        Retrieve all hashtags used by a specific agent.
        :param agent_id:
        :param from_round:
        :param to_round:
        :return:
        """
        if from_round is not None and to_round is not None:
            query = "SELECT h.hashtag FROM post_hashtags as ph, post as p, hashtags as h WHERE p.user_id = ? AND p.id = ph.post_id AND ph.hashtag_id = h.id AND ph.round >= ? AND ph.round <= ?"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT h.hashtag FROM post_hashtags as ph, post as p, hashtags as h WHERE p.user_id = ? AND p.id = ph.post_id AND ph.hashtag_id = h.id"
            data = self.__execute_query(query, (agent_id,))

        hashtags = defaultdict(int)
        for row in data:
            hashtags[row[0]] += 1

        return hashtags

    def agent_interests(self, agent_id, from_round=None, to_round=None):
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

    def agent_emotions(self, agent_id, from_round=None, to_round=None):
        """
        Retrieve the sentiment profile of a specific agent.
        :param agent_id:
        :param from_round:
        :param to_round:
        :return:
        """
        if from_round is not None and to_round is not None:
            query = "SELECT e.emotion FROM post as p, post_emotions as pe, emotions as e WHERE p.user_id = ? AND p.id = pe.post_id AND e.id = pe.emotion_id AND round >= ? AND round <= ?"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT e.emotion FROM post as p, post_emotions as pe, emotions as e WHERE p.user_id = ? AND p.id = pe.post_id AND e.id = pe.emotion_id"
            data = self.__execute_query(query, (agent_id,))

        emotion = defaultdict(int)
        for row in data:
            emotion[row[0]] += 1

        return emotion

    def agent_toxicity(self, agent_id, from_round=None, to_round=None):
        """
        Retrieve the toxicity profile of a specific agent.
        :param agent_id:
        :param from_round:
        :param to_round:
        :return:
        """
        if from_round is not None and to_round is not None:
            query = "SELECT * FROM post as p, post_toxicity as pt WHERE p.user_id = ? AND p.id = pt.post_id AND round >= ? AND round <= ? order by round ASC"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT * FROM post as p, post_toxicity as pt WHERE p.user_id = ? AND p.id = pt.post_id order by round ASC"
            data = self.__execute_query(query, (agent_id,))

        toxicity = []
        for row in data:
            toxicity.append(
                {
                    "toxicity": row[2],
                    "severe_toxicity": row[3],
                    "identity_attack": row[4],
                    "insult": row[5],
                    "profanity": row[6],
                    "threat": row[7],
                    "sexual_explicit": row[8],
                    "flirtation": row[9],
                }
            )

        return toxicity

    # Network Extraction Methods #

    def ego_network_follower(self, agent_id, from_round=None, to_round=None):
        """
        Retrieve the ego network of a specific agent.
        :param agent_id:
        :param from_round:
        :param to_round:
        :return:
        """
        if from_round is not None and to_round is not None:
            query = "SELECT user_id, follower_id, action FROM follow WHERE user_id = ? AND round >= ? AND round <= ? order by round ASC"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT user_id, follower_id, action FROM follow WHERE user_id = ? order by round ASC"
            data = self.__execute_query(query, (agent_id,))

        ego_network = defaultdict(list)
        for row in data:
            ego_network[row[1]].append(row[2])

        # if len(ego_network[i]) is even, the edge has been removed and need to be removed from the ego network
        for i in list(ego_network.keys()):
            if len(ego_network[i]) % 2 == 0:
                ego_network.pop(i, None)

        g = nx.DiGraph()
        for n in ego_network.keys():
            g.add_edge(agent_id, n)

        return g

    def ego_network_following(self, agent_id, from_round=None, to_round=None):
            """
            Retrieve the ego network of a specific agent.
            :param agent_id:
            :param from_round:
            :param to_round:
            :return:
            """
            if from_round is not None and to_round is not None:
                query = "SELECT follower_id, user_id, action FROM follow WHERE follower_id = ? AND round >= ? AND round <= ? order by round ASC"
                data = self.__execute_query(query, (agent_id, from_round, to_round))
            else:
                query = "SELECT follower_id, user_id, action FROM follow WHERE follower_id = ? order by round ASC"
                data = self.__execute_query(query, (agent_id,))

            ego_network = defaultdict(list)
            for row in data:
                ego_network[row[1]].append(row[2])

            # if len(ego_network[i]) is even, the edge has been removed and need to be removed from the ego network
            for i in list(ego_network.keys()):
                if len(ego_network[i]) % 2 == 0:
                    ego_network.pop(i, None)

            g = nx.DiGraph()
            for n in ego_network.keys():
                g.add_edge(n, agent_id)

            return g

    def ego_network(self, agent_id, from_round=None, to_round=None):
            """
            Retrieve the ego network of a specific agent.
            :param agent_id:
            :param from_round:
            :param to_round:
            :return:
            """
            following = self.ego_network_following(agent_id, from_round, to_round)
            follower = self.ego_network_follower(agent_id, from_round, to_round)

            g = nx.compose(following, follower)

            return g

    def social_network(self, from_round=None, to_round=None, agent_ids=None):
        """
        Retrieve the networks of all agents.
        :param from_round:
        :param to_round:
        :param agent_ids: List of agent IDs to include in the network. If None, all agents are included.
        :return:
        """
        if agent_ids is None:
            agents = self.agents()
            agent_ids = [a.id for a in agents.get_agents()]

        networks = {}

        for agent in agent_ids:
            networks[agent] = self.ego_network(agent, from_round, to_round)

        # merge the networks
        merged_network = nx.compose_all(networks.values())

        return merged_network

    def mention_ego_network(self, agent_id, from_round=None, to_round=None):
        """
        Retrieve the mention network of a specific agent.
        :param agent_id:
        :param from_round:
        :param to_round:
        :return:
        """
        if from_round is not None and to_round is not None:
            query = "SELECT m.user_id FROM post as p, mentions as m WHERE p.user_id = ? AND p.id = m.post_id AND round >= ? AND round <= ?"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT m.user_id FROM post as p, mentions as m WHERE p.user_id = ? AND p.id = m.post_id "
            data = self.__execute_query(query, (agent_id,))

        mentions = defaultdict(int)
        for row in data:
            mentions[row[0]] += 1

        g = nx.DiGraph()
        for n, v in mentions.items():
            g.add_edge(agent_id, n, weight=v)

        return g

    def mention_network(self, from_round=None, to_round=None, agent_ids=None):
        """
        Retrieve the mention networks of all agents.
        :param from_round:
        :param to_round:
        :param agent_ids: List of agent IDs to include in the network. If None, all agents are included.
        :return:
        """
        if agent_ids is None:
            agents = self.agents()
            agent_ids = [a.id for a in agents.get_agents()]

        networks = {}

        for agent in agent_ids:
            networks[agent] = self.mention_ego_network(agent, from_round, to_round)

        # merge the networks
        merged_network = nx.compose_all(networks.values())

        return merged_network