import os
import sqlite3
from collections import defaultdict, namedtuple
from functools import wraps
from urllib.parse import urlparse

import networkx as nx

from ysights.models.Agents import Agent, Agents
from ysights.models.Posts import Post, Posts

# Try to import psycopg2, but don't fail if it's not available
try:
    import psycopg2
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

UserPost = namedtuple("UserPost", ["agent_id", "post_id"])


class YDataHandler:
    """
    Main handler for YSocial simulation database operations.

    This class provides a comprehensive interface for querying and analyzing data
    from YSocial simulations. It manages database connections, retrieves agent and
    post information, extracts social networks, and provides various analytical
    methods for understanding simulation dynamics.

    Supports both SQLite and PostgreSQL databases with the same table structure.

    :param db_path: Path to SQLite database file or PostgreSQL connection string
    :type db_path: str

    :ivar str db_path: Database path or connection string
    :ivar str db_type: Type of database ('sqlite' or 'postgresql')
    :ivar connection: Active database connection (None when not connected)

    Example:
        Basic usage with SQLite::

            from ysights import YDataHandler

            # Initialize handler with SQLite database
            ydh = YDataHandler('path/to/simulation_data.db')

            # Get time range of simulation
            time_info = ydh.time_range()
            print(f"Simulation runs from round {time_info['min_round']} to {time_info['max_round']}")

            # Get all agents
            agents = ydh.agents()
            print(f"Total agents: {len(agents.get_agents())}")

        Basic usage with PostgreSQL::

            from ysights import YDataHandler

            # Initialize handler with PostgreSQL database
            ydh = YDataHandler('postgresql://user:password@localhost:5432/ysocial_db')

            # Use the same methods as with SQLite
            agents = ydh.agents()
            print(f"Total agents: {len(agents.get_agents())}")

            # Get posts by specific agent with enriched data
            agent_posts = ydh.posts_by_agent(agent_id=5, enrich_dimensions=['sentiment', 'hashtags'])
            for post in agent_posts.get_posts():
                print(f"Post: {post.text}")
                print(f"Sentiment: {post.sentiment}")

            # Extract social network
            network = ydh.social_network(from_round=0, to_round=100)
            print(f"Network has {network.number_of_nodes()} nodes and {network.number_of_edges()} edges")

    Note:
        Database connections are automatically managed through the internal
        decorator ``_handle_db_connection``. Methods that query the database
        will automatically open and close connections as needed.

    See Also:
        :class:`ysights.models.Agents.Agents`: Container for agent collections
        :class:`ysights.models.Posts.Posts`: Container for post collections
    """

    def __init__(self, db_path):
        """
        Initialize the YDataHandler with database connection information.

        :param db_path: Path to SQLite database file or PostgreSQL connection string.
                       For SQLite: 'path/to/database.db'
                       For PostgreSQL: 'postgresql://user:password@host:port/database'
                                      or 'postgres://user:password@host:port/database'
        :type db_path: str
        :raises FileNotFoundError: If the SQLite database file does not exist when first accessed
        :raises ImportError: If PostgreSQL connection string is used but psycopg2 is not installed

        Example::

            # SQLite
            ydh = YDataHandler('simulation_results/data.db')

            # PostgreSQL
            ydh = YDataHandler('postgresql://user:password@localhost:5432/ysocial_db')
        """
        self.db_path = db_path
        self.connection = None

        # Detect database type
        if db_path.startswith("postgresql://") or db_path.startswith("postgres://"):
            self.db_type = "postgresql"
            if not PSYCOPG2_AVAILABLE:
                raise ImportError(
                    "psycopg2 is required for PostgreSQL support. "
                    "Install it with: pip install psycopg2-binary"
                )
        else:
            self.db_type = "sqlite"

    # Connection handling methods

    from functools import wraps

    def _handle_db_connection(func):
        """
        Decorator to handle database connection management for methods.

        This decorator ensures that database connections are properly established
        before method execution and closed afterwards, preventing connection leaks
        and ensuring clean resource management.

        :param func: The function to be wrapped
        :type func: callable
        :return: Wrapped function with connection management
        :rtype: callable

        Note:
            This is an internal decorator used to wrap methods that require
            database access. It should not be called directly by users.
        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            """
            Wrapper function to ensure the database connection is established.

            :param self: Instance of YDataHandler
            :param args: Positional arguments for the wrapped function
            :param kwargs: Keyword arguments for the wrapped function
            :return: Result from the wrapped function
            """
            self.__connect()
            result = func(self, *args, **kwargs)
            self.__close()  # Ensure the connection is closed after the operation
            return result

        return wrapper

    def __connect(self):
        """
        Establish connection to the database (SQLite or PostgreSQL).

        :raises FileNotFoundError: If the SQLite database file does not exist
        :raises Exception: If PostgreSQL connection fails
        """
        if self.db_type == "sqlite":
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database file {self.db_path} does not exist.")
            self.connection = sqlite3.connect(self.db_path)
        elif self.db_type == "postgresql":
            self.connection = psycopg2.connect(self.db_path)

    def __close(self):
        """
        Close the database connection if it is open.

        This method safely closes the connection and resets it to None.
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    def __get_cursor(self):
        """
        Get a database cursor for executing SQL queries.

        :return: Database cursor
        :rtype: sqlite3.Cursor or psycopg2.cursor
        :raises FileNotFoundError: If database connection is not established
        """
        if not self.connection:
            raise FileNotFoundError("Database connection is not established.")
        return self.connection.cursor()

    def __convert_query_for_db(self, query, params=None):
        """
        Convert query parameters from SQLite format to database-specific format.

        :param query: SQL query string with ? placeholders (SQLite style)
        :type query: str
        :param params: Query parameters
        :type params: tuple or list
        :return: Tuple of (converted_query, params)
        :rtype: tuple
        """
        if self.db_type == "postgresql":
            # Convert ? placeholders to %s for PostgreSQL
            count = 0
            converted_query = ""
            for char in query:
                if char == "?":
                    count += 1
                    converted_query += "%s"
                else:
                    converted_query += char
            return converted_query, params
        else:
            # SQLite - no conversion needed
            return query, params

    def __execute_query(self, query, params=None):
        """
        Execute an SQL query and return the results.

        :param query: SQL query string to execute
        :type query: str
        :param params: Optional parameters for parameterized queries
        :type params: tuple or list, optional
        :return: Query results as list of tuples
        :rtype: list
        :raises FileNotFoundError: If database connection is not established
        """
        if not self.connection:
            raise FileNotFoundError("Database connection is not established.")

        # Convert query to database-specific format
        query, params = self.__convert_query_for_db(query, params)

        cursor = self.connection.cursor()
        cursor.execute(query, params or [])
        return cursor.fetchall()

    @_handle_db_connection
    def custom_query(self, query):
        """
        Execute a custom SQL query and return the results.

        This method allows execution of arbitrary SQL queries against the database.
        Use with caution and ensure proper SQL injection protection for user inputs.

        :param query: SQL query string to execute
        :type query: str
        :return: Query results as list of tuples
        :rtype: list

        Example::

            ydh = YDataHandler('path/to/database.db')

            # Execute custom query
            results = ydh.custom_query("SELECT COUNT(*) FROM post WHERE round < 100")
            print(f"Posts in first 100 rounds: {results[0][0]}")

            # More complex query
            query = '''
                SELECT u.username, COUNT(p.id) as post_count
                FROM user_mgmt u
                JOIN post p ON u.id = p.user_id
                GROUP BY u.id
                ORDER BY post_count DESC
                LIMIT 10
            '''
            top_posters = ydh.custom_query(query)
            for username, count in top_posters:
                print(f"{username}: {count} posts")

        Warning:
            Be careful with user-provided input to avoid SQL injection vulnerabilities.
            Consider using parameterized queries when possible.
        """
        return self.__execute_query(query)

    # Time
    @_handle_db_connection
    def time_range(self):
        """
        Retrieve the time range covered by the simulation.

        Returns the minimum and maximum round IDs present in the database,
        representing the temporal extent of the simulation data.

        :return: Dictionary with 'min_round' and 'max_round' keys
        :rtype: dict
        :raises ValueError: If no rounds are found in the database

        Example::

            ydh = YDataHandler('path/to/database.db')

            time_info = ydh.time_range()
            print(f"Simulation starts at round: {time_info['min_round']}")
            print(f"Simulation ends at round: {time_info['max_round']}")
            print(f"Total rounds: {time_info['max_round'] - time_info['min_round'] + 1}")
        """
        query = "SELECT MIN(id), MAX(id) FROM rounds"
        data = self.__execute_query(query)
        if data and data[0]:
            return {"min_round": data[0][0], "max_round": data[0][1]}
        else:
            raise ValueError("No rounds found in the database.")

    @_handle_db_connection
    def round_to_time(self, round_id):
        """
        Convert a round ID to its corresponding day and hour representation.

        :param round_id: The round ID to convert
        :type round_id: int
        :return: Dictionary with 'day' and 'hour' keys
        :rtype: dict
        :raises ValueError: If the round ID does not exist in the database

        Example::

            ydh = YDataHandler('path/to/database.db')

            time_info = ydh.round_to_time(round_id=250)
            print(f"Round 250 occurred on day {time_info['day']} at hour {time_info['hour']}")

            # Converting multiple rounds
            for round_id in [100, 200, 300]:
                time = ydh.round_to_time(round_id)
                print(f"Round {round_id}: Day {time['day']}, Hour {time['hour']}")
        """
        query = "SELECT day, hour FROM rounds WHERE id = ?"
        data = self.__execute_query(query, (round_id,))
        if data:
            return {"day": data[0][0], "hour": data[0][1]}
        else:
            raise ValueError(f"Round ID {round_id} does not exist in the database.")

    @_handle_db_connection
    def time_to_round(self, day, hour=0):
        """
        Convert a day and hour to the corresponding round ID.

        :param day: The simulation day
        :type day: int
        :param hour: The hour within the day (default: 0)
        :type hour: int
        :return: The round ID corresponding to the specified time
        :rtype: int
        :raises ValueError: If no round exists for the specified day and hour

        Example::

            ydh = YDataHandler('path/to/database.db')

            # Get round ID for day 10, hour 5
            round_id = ydh.time_to_round(day=10, hour=5)
            print(f"Day 10, Hour 5 is round {round_id}")

            # Get round ID for start of day 5
            round_id = ydh.time_to_round(day=5)
            print(f"Day 5 starts at round {round_id}")
        """
        query = "SELECT id FROM rounds WHERE day = ? AND hour = ?"
        data = self.__execute_query(query, (day, hour))
        if data:
            return data[0][0]
        else:
            raise ValueError(f"No round found for day {day} and hour {hour}.")

    # Agents and Posts methods
    @_handle_db_connection
    def number_of_agents(self):
        """
        Get the total number of agents in the simulation.

        :return: Total count of agents
        :rtype: int

        Example::

            ydh = YDataHandler('path/to/database.db')

            agent_count = ydh.number_of_agents()
            print(f"Total agents in simulation: {agent_count}")
        """
        query = "SELECT COUNT(*) FROM user_mgmt"
        data = self.__execute_query(query)
        return data[0][0] if data else 0

    @_handle_db_connection
    def agents(self):
        """
        Retrieve all agents from the simulation database.

        Returns an Agents collection containing all agent records with their
        complete demographic and behavioral attributes.

        :return: Collection of all agents
        :rtype: Agents

        Example::

            ydh = YDataHandler('path/to/database.db')

            agents = ydh.agents()
            print(f"Total agents: {len(agents.get_agents())}")

            # Analyze agent demographics
            for agent in agents.get_agents():
                print(f"Agent {agent.id}: {agent.username}")
                print(f"  Age: {agent.age}, Gender: {agent.gender}")
                print(f"  Leaning: {agent.leaning}")
                print(f"  Personality: {agent.personality}")

        See Also:
            :meth:`agents_by_feature`: Filter agents by specific attributes
            :class:`ysights.models.Agents.Agents`: Agents collection class
        """
        query = "SELECT * FROM user_mgmt"
        data = self.__execute_query(query)
        agents = Agents()
        for row in data:
            ag = Agent(row)
            agents.add_agent(ag)
        return agents

    @_handle_db_connection
    def agents_by_feature(self, feature, value):
        """
        Retrieve agents filtered by a specific feature value.

        Allows querying agents based on any column in the user_mgmt table,
        such as leaning, gender, role, education, etc.

        :param feature: The column name to filter by (e.g., 'leaning', 'gender', 'role')
        :type feature: str
        :param value: The value to match for the specified feature
        :type value: str or int
        :return: Collection of matching agents
        :rtype: Agents

        Example::

            ydh = YDataHandler('path/to/database.db')

            # Get all agents with left-leaning political orientation
            left_agents = ydh.agents_by_feature('leaning', 'left')
            print(f"Left-leaning agents: {len(left_agents.get_agents())}")

            # Get all female agents
            female_agents = ydh.agents_by_feature('gender', 'female')

            # Get all agents with college education
            college_agents = ydh.agents_by_feature('education', 'college')

            for agent in college_agents.get_agents():
                print(f"{agent.username} - {agent.profession}")

        Warning:
            The feature parameter is directly inserted into SQL query. Ensure
            it comes from trusted sources to prevent SQL injection.

        See Also:
            :meth:`agents`: Get all agents without filtering
        """
        query = f"SELECT * FROM user_mgmt WHERE {feature} = ?"
        data = self.__execute_query(query, (value,))
        agents = Agents()
        for row in data:
            ag = Agent(row)
            agents.add_agent(ag)
        return agents

    @_handle_db_connection
    def agent_mapping(self):
        """
        Get a mapping of agent IDs to usernames.

        Provides a convenient dictionary for looking up agent usernames by their IDs.

        :return: Dictionary mapping agent IDs to usernames
        :rtype: dict

        Example::

            ydh = YDataHandler('path/to/database.db')

            mapping = ydh.agent_mapping()
            print(f"Agent 5's username: {mapping[5]}")

            # Use mapping to display usernames in analysis
            post_counts = {}  # hypothetical post count data
            for agent_id, count in post_counts.items():
                username = mapping.get(agent_id, 'Unknown')
                print(f"{username}: {count} posts")
        """
        query = "SELECT id, username FROM user_mgmt"
        data = self.__execute_query(query)
        agent_mapping = {}
        for row in data:
            agent_mapping[row[0]] = row[1]
        return agent_mapping

    @_handle_db_connection
    def agent_post_ids(self, agent_id):
        """
        Get all post IDs created by a specific agent.

        :param agent_id: The ID of the agent
        :type agent_id: int
        :return: Dictionary of post IDs (post_id -> post_id mapping)
        :rtype: dict

        Example::

            ydh = YDataHandler('path/to/database.db')

            post_ids = ydh.agent_post_ids(agent_id=5)
            print(f"Agent 5 created {len(post_ids)} posts")
            print(f"Post IDs: {list(post_ids.keys())}")

        See Also:
            :meth:`posts_by_agent`: Get full Post objects instead of just IDs
        """
        query = "SELECT id FROM post WHERE user_id = ?"
        data = self.__execute_query(query, (agent_id,))
        posts = {}
        for row in data:
            post_id = row[0]
            posts[post_id] = post_id
        return posts

    @_handle_db_connection
    def posts(self):
        """
        Retrieve all posts from the simulation database.

        Returns a Posts collection containing all post records without enrichment.
        For enriched posts with sentiment, hashtags, etc., use :meth:`posts_by_agent`
        with enrich_dimensions parameter.

        :return: Collection of all posts
        :rtype: Posts

        Example::

            ydh = YDataHandler('path/to/database.db')

            posts = ydh.posts()
            print(f"Total posts in simulation: {len(posts.get_posts())}")

            # Analyze post distribution
            rounds = [post.round for post in posts.get_posts()]
            print(f"Posts range from round {min(rounds)} to {max(rounds)}")

        See Also:
            :meth:`posts_by_agent`: Get posts by specific agent with enrichment options
            :class:`ysights.models.Posts.Posts`: Posts collection class
        """
        query = "SELECT * FROM post"
        data = self.__execute_query(query)
        posts = Posts()
        for row in data:
            post = Post(row)
            posts.add_post(post)
        return posts

    @_handle_db_connection
    def posts_by_agent(self, agent_id, enrich_dimensions: list = ["all"]):
        """
        Retrieve posts created by a specific agent with optional enrichment.

        This method allows selective enrichment of posts with additional data
        such as sentiment scores, hashtags, topics, mentions, emotions, toxicity,
        and reactions. Use specific dimensions for faster queries or 'all' for
        complete enrichment.

        :param agent_id: The ID of the agent whose posts to retrieve
        :type agent_id: int
        :param enrich_dimensions: List of dimensions to enrich. Options:
                                 'sentiment', 'hashtags', 'mentions', 'emotions',
                                 'topics', 'toxicity', 'reactions', 'all', or []
        :type enrich_dimensions: list[str]
        :return: Collection of posts by the specified agent
        :rtype: Posts

        Example::

            ydh = YDataHandler('path/to/database.db')

            # Get posts with full enrichment
            posts = ydh.posts_by_agent(agent_id=5, enrich_dimensions=['all'])
            for post in posts.get_posts():
                print(f"Post: {post.text}")
                print(f"Sentiment: {post.sentiment}")
                print(f"Hashtags: {post.hashtags}")
                print(f"Topics: {post.topics}")

            # Get posts with selective enrichment (faster)
            posts = ydh.posts_by_agent(agent_id=5, enrich_dimensions=['sentiment', 'hashtags'])

            # Get posts without enrichment
            posts = ydh.posts_by_agent(agent_id=5, enrich_dimensions=[])

        See Also:
            :meth:`Post.enrich_post`: Method that performs the enrichment
            :meth:`posts`: Get all posts without filtering
        """
        query = "SELECT * FROM post WHERE user_id = ?"
        data = self.__execute_query(query, (agent_id,))
        posts = Posts()
        for row in data:
            post = Post(row)
            if len(enrich_dimensions) > 0:
                # Enrich the post with additional data
                post.enrich_post(self.__get_cursor(), enrich_dimensions)
            posts.add_post(post)
        return posts

    @_handle_db_connection
    def agent_id_by_post_id(self, post_id):
        """
        Get the agent ID who created a specific post.

        :param post_id: The ID of the post
        :type post_id: int
        :return: The ID of the agent who created the post
        :rtype: int
        :raises ValueError: If the post ID does not exist in the database

        Example::

            ydh = YDataHandler('path/to/database.db')

            agent_id = ydh.agent_id_by_post_id(post_id=123)
            print(f"Post 123 was created by agent {agent_id}")

            # Get username of post author
            mapping = ydh.agent_mapping()
            username = mapping[agent_id]
            print(f"Author: {username}")
        """
        query = "SELECT user_id FROM post WHERE id = ?"
        data = self.__execute_query(query, (post_id,))
        if data:
            return data[0][0]
        else:
            raise ValueError(f"Post ID {post_id} does not exist in the database.")

    # Recommendations and visibility methods
    @_handle_db_connection
    def agent_recommendations(self, agent_id, from_round=None, to_round=None):
        """
        Get recommendations received by a specific agent.

        Returns the posts recommended to an agent, optionally filtered by time range.
        Each post is represented as a UserPost namedtuple containing the post author's
        ID and the post ID, with a count of how many times it was recommended.

        :param agent_id: The ID of the agent
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping UserPost to recommendation count
        :rtype: dict[UserPost, int]

        Example::

            ydh = YDataHandler('path/to/database.db')

            # Get all recommendations for agent 5
            recs = ydh.agent_recommendations(agent_id=5)
            print(f"Agent 5 received {len(recs)} unique post recommendations")

            for user_post, count in recs.items():
                print(f"Post {user_post.post_id} by agent {user_post.agent_id}: {count} times")

            # Get recommendations in specific time range
            recs = ydh.agent_recommendations(agent_id=5, from_round=100, to_round=200)
            print(f"Recommendations in rounds 100-200: {len(recs)}")

        See Also:
            :meth:`recommendations_per_post`: Get recommendation counts per post
            :meth:`agent_posts_visibility`: Get visibility of agent's own posts
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

    @_handle_db_connection
    def agent_posts_visibility(
        self, agent_id, rec_stats, from_round=None, to_round=None
    ):
        """
        Get visibility metrics for posts created by a specific agent.

        Calculates how many times each of the agent's posts was recommended to others.
        This provides insight into the reach and visibility of an agent's content.

        :param agent_id: The ID of the agent whose posts to analyze
        :type agent_id: int
        :param rec_stats: Dictionary of post IDs to their recommendation counts
                         (typically from recommendations_per_post())
        :type rec_stats: dict[int, int]
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping post IDs to recommendation counts
        :rtype: dict[int, int]

        Example::

            ydh = YDataHandler('path/to/database.db')

            # First get overall recommendation stats
            rec_stats = ydh.recommendations_per_post()

            # Then get visibility for specific agent
            visibility = ydh.agent_posts_visibility(agent_id=5, rec_stats=rec_stats)
            print(f"Agent 5's post visibility:")
            for post_id, count in visibility.items():
                print(f"  Post {post_id} was recommended {count} times")

            # Get visibility in specific time range
            visibility = ydh.agent_posts_visibility(
                agent_id=5, rec_stats=rec_stats,
                from_round=100, to_round=200
            )

        See Also:
            :meth:`recommendations_per_post`: Get recommendation statistics
            :meth:`agent_recommendations`: Get recommendations received by agent
        """
        if from_round is not None and to_round is not None:
            query = "SELECT p.id FROM post as p WHERE p.user_id = ? AND p.round >= ? AND p.round <= ?"
            data = self.__execute_query(query, (agent_id, from_round, to_round))
        else:
            query = "SELECT p.id FROM post as p WHERE p.user_id = ?"
            data = self.__execute_query(query, (agent_id,))

        posts = {int(row[0]): None for row in data}
        # filter rec_stats to only include posts made by the agent
        filtered_recs = {k: v for k, v in rec_stats.items() if k in posts}
        return filtered_recs

    @_handle_db_connection
    def recommendations_per_post(self):
        """
        Get recommendation counts for all posts in the simulation.

        Aggregates how many times each post was recommended across all agents
        and all rounds. Useful for identifying popular or viral content.

        :return: Dictionary mapping post IDs to their total recommendation counts
        :rtype: dict[int, int]

        Example::

            ydh = YDataHandler('path/to/database.db')

            rec_stats = ydh.recommendations_per_post()

            # Find most recommended posts
            sorted_posts = sorted(rec_stats.items(), key=lambda x: x[1], reverse=True)
            print("Top 10 most recommended posts:")
            for post_id, count in sorted_posts[:10]:
                print(f"  Post {post_id}: {count} recommendations")

            # Use for visibility analysis
            visibility = ydh.agent_posts_visibility(agent_id=5, rec_stats=rec_stats)

        See Also:
            :meth:`recommendations_per_post_per_user`: Get per-user recommendation data
            :meth:`agent_posts_visibility`: Use stats for visibility analysis
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

    @_handle_db_connection
    def recommendations_per_post_per_user(self):
        """
        Get detailed recommendation data including per-user reading history.

        Returns both aggregated recommendation counts per post and a mapping of
        which posts each user received in their recommendations. This provides
        detailed insight into content distribution patterns.

        :return: Tuple of (post_recs, user_to_posts_read) where:
                 - post_recs: dict mapping post_id to recommendation count
                 - user_to_posts_read: dict mapping user_id to list of post_ids they received
        :rtype: tuple[dict[int, int], dict[int, list[int]]]

        Example::

            ydh = YDataHandler('path/to/database.db')

            post_recs, user_reading_history = ydh.recommendations_per_post_per_user()

            # Analyze post popularity
            print("Most recommended posts:")
            for post_id, count in sorted(post_recs.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  Post {post_id}: {count} recommendations")

            # Analyze user reading patterns
            user_id = 5
            posts_seen = user_reading_history[user_id]
            print(f"Agent {user_id} saw {len(posts_seen)} posts")
            print(f"Average recommendations per post: {sum(post_recs.values()) / len(post_recs):.2f}")

        See Also:
            :meth:`recommendations_per_post`: Simpler version with just post counts
            :meth:`agent_recommendations`: Get recommendations for specific agent
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
    @_handle_db_connection
    def agent_reactions(self, agent_id, from_round=None, to_round=None):
        """
        Get all reactions made by a specific agent.

        Returns reactions (likes, loves, etc.) that an agent has given to posts,
        optionally filtered by time range. Results are grouped by reaction type.

        :param agent_id: The ID of the agent
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping reaction types to lists of post IDs
        :rtype: dict[str, list[int]]

        Example::

            ydh = YDataHandler('path/to/database.db')

            reactions = ydh.agent_reactions(agent_id=5)
            print(f"Agent 5's reactions:")
            for reaction_type, post_ids in reactions.items():
                print(f"  {reaction_type}: {len(post_ids)} posts")

            # Reactions in specific time range
            reactions = ydh.agent_reactions(agent_id=5, from_round=100, to_round=200)
            like_count = len(reactions.get('like', []))
            print(f"Likes in rounds 100-200: {like_count}")

        See Also:
            :meth:`agent_hashtags`: Get hashtags used by agent
            :meth:`agent_interests`: Get interests of agent
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

    @_handle_db_connection
    def agent_hashtags(self, agent_id, from_round=None, to_round=None):
        """
        Get hashtags used by a specific agent in their posts.

        Returns all hashtags the agent has used, with counts indicating frequency
        of use. Optionally filter by time range.

        :param agent_id: The ID of the agent
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping hashtags to their usage counts
        :rtype: dict[str, int]

        Example::

            ydh = YDataHandler('path/to/database.db')

            hashtags = ydh.agent_hashtags(agent_id=5)
            print("Agent 5's most used hashtags:")
            for tag, count in sorted(hashtags.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  #{tag}: {count} times")

            # Hashtags in specific period
            recent_tags = ydh.agent_hashtags(agent_id=5, from_round=500, to_round=1000)
            print(f"Used {len(recent_tags)} different hashtags in rounds 500-1000")

        See Also:
            :meth:`agent_interests`: Get interests of agent
            :meth:`agent_topics`: Get topics agent engages with
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

    @_handle_db_connection
    def agent_interests(self, agent_id, from_round=None, to_round=None):
        """
        Get the interest profile of a specific agent.

        Returns the interests/topics that the agent is associated with, including
        counts indicating strength or frequency of each interest. Optionally filter
        by time range.

        :param agent_id: The ID of the agent
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping interests to their frequency counts
        :rtype: dict[str, int]

        Example::

            ydh = YDataHandler('path/to/database.db')

            interests = ydh.agent_interests(agent_id=5)
            print("Agent 5's interest profile:")
            for interest, count in sorted(interests.items(), key=lambda x: x[1], reverse=True):
                print(f"  {interest}: {count}")

            # Track interest evolution
            early_interests = ydh.agent_interests(agent_id=5, from_round=0, to_round=500)
            late_interests = ydh.agent_interests(agent_id=5, from_round=500, to_round=1000)

            new_interests = set(late_interests.keys()) - set(early_interests.keys())
            print(f"New interests acquired: {new_interests}")

        See Also:
            :meth:`agent_hashtags`: Get hashtags used by agent
            :meth:`agent_emotions`: Get emotional profile of agent
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

    @_handle_db_connection
    def agent_emotions(self, agent_id, from_round=None, to_round=None):
        """
        Get the emotional profile of a specific agent's posts.

        Returns emotions detected in the agent's posts, with counts indicating
        how frequently each emotion appears. Optionally filter by time range.

        :param agent_id: The ID of the agent
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping emotions to their frequency counts
        :rtype: dict[str, int]

        Example::

            ydh = YDataHandler('path/to/database.db')

            emotions = ydh.agent_emotions(agent_id=5)
            print("Agent 5's emotional expression:")
            for emotion, count in sorted(emotions.items(), key=lambda x: x[1], reverse=True):
                print(f"  {emotion}: {count} posts")

            # Compare emotional states over time
            early_emotions = ydh.agent_emotions(agent_id=5, from_round=0, to_round=500)
            late_emotions = ydh.agent_emotions(agent_id=5, from_round=500, to_round=1000)

            joy_change = late_emotions.get('joy', 0) - early_emotions.get('joy', 0)
            print(f"Change in joy expression: {joy_change}")

        See Also:
            :meth:`agent_toxicity`: Get toxicity profile
            :meth:`agent_interests`: Get interest profile
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

    @_handle_db_connection
    def agent_toxicity(self, agent_id, from_round=None, to_round=None):
        """
        Get the toxicity profile of a specific agent's posts.

        Returns detailed toxicity scores for each of the agent's posts, including
        overall toxicity and specific toxic dimensions (severe toxicity, identity
        attacks, insults, profanity, threats, sexual content, flirtation).
        Optionally filter by time range.

        :param agent_id: The ID of the agent
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: List of dictionaries, each containing toxicity scores for a post
        :rtype: list[dict]

        Example::

            ydh = YDataHandler('path/to/database.db')

            toxicity_data = ydh.agent_toxicity(agent_id=5)
            print(f"Agent 5 toxicity analysis over {len(toxicity_data)} posts:")

            # Calculate average toxicity
            if toxicity_data:
                avg_tox = sum(p['toxicity'] for p in toxicity_data) / len(toxicity_data)
                print(f"Average toxicity: {avg_tox:.3f}")

                # Check for specific toxic behaviors
                high_profanity = [p for p in toxicity_data if p['profanity'] > 0.7]
                print(f"Posts with high profanity: {len(high_profanity)}")

            # Compare toxicity over time periods
            early_tox = ydh.agent_toxicity(agent_id=5, from_round=0, to_round=500)
            late_tox = ydh.agent_toxicity(agent_id=5, from_round=500, to_round=1000)

        Note:
            Toxicity scores are typically in the range [0, 1] where higher values
            indicate more toxic content.

        See Also:
            :meth:`agent_emotions`: Get emotional profile
            :meth:`posts_by_agent`: Get full post objects with toxicity data
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
    @_handle_db_connection
    def ego_network_follower(self, agent_id, from_round=None, to_round=None):
        """
        Extract the follower ego network for a specific agent.

        Returns a directed network showing agents who follow the specified agent.
        The network accounts for follow/unfollow dynamics, keeping only active
        connections at the end of the time period.

        :param agent_id: The ID of the agent (the "ego")
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Directed graph with edges pointing from ego to followers
        :rtype: networkx.DiGraph

        Example::

            import networkx as nx
            from ysights import YDataHandler

            ydh = YDataHandler('path/to/database.db')

            # Get follower network for agent 5
            follower_net = ydh.ego_network_follower(agent_id=5)
            print(f"Agent 5 has {follower_net.number_of_nodes() - 1} followers")
            print(f"Follower IDs: {list(follower_net.successors(5))}")

            # Get follower network in specific time period
            recent_followers = ydh.ego_network_follower(agent_id=5, from_round=500, to_round=1000)

        Note:
            This method tracks follow/unfollow actions. If an edge has been
            followed and then unfollowed (even number of actions), it is removed
            from the final network.

        See Also:
            :meth:`ego_network_following`: Get accounts the agent follows
            :meth:`ego_network`: Get complete ego network (both followers and following)
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

    @_handle_db_connection
    def ego_network_following(self, agent_id, from_round=None, to_round=None):
        """
        Extract the following ego network for a specific agent.

        Returns a directed network showing agents that the specified agent follows.
        The network accounts for follow/unfollow dynamics, keeping only active
        connections at the end of the time period.

        :param agent_id: The ID of the agent (the "ego")
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Directed graph with edges pointing from accounts followed to ego
        :rtype: networkx.DiGraph

        Example::

            import networkx as nx
            from ysights import YDataHandler

            ydh = YDataHandler('path/to/database.db')

            # Get following network for agent 5
            following_net = ydh.ego_network_following(agent_id=5)
            print(f"Agent 5 follows {following_net.number_of_nodes() - 1} accounts")
            print(f"Following IDs: {list(following_net.predecessors(5))}")

            # Compare early vs late following behavior
            early = ydh.ego_network_following(agent_id=5, from_round=0, to_round=500)
            late = ydh.ego_network_following(agent_id=5, from_round=500, to_round=1000)
            print(f"Early following count: {early.number_of_nodes() - 1}")
            print(f"Late following count: {late.number_of_nodes() - 1}")

        Note:
            This method tracks follow/unfollow actions. If an edge has been
            followed and then unfollowed (even number of actions), it is removed
            from the final network.

        See Also:
            :meth:`ego_network_follower`: Get followers of the agent
            :meth:`ego_network`: Get complete ego network (both followers and following)
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

    @_handle_db_connection
    def ego_network(self, agent_id, from_round=None, to_round=None):
        """
        Extract the complete ego network for a specific agent.

        Returns a directed network combining both followers (who follow the agent)
        and following (accounts the agent follows). This provides a comprehensive
        view of the agent's social connections.

        :param agent_id: The ID of the agent (the "ego")
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Directed graph representing the complete ego network
        :rtype: networkx.DiGraph

        Example::

            import networkx as nx
            from ysights import YDataHandler

            ydh = YDataHandler('path/to/database.db')

            # Get complete ego network for agent 5
            ego_net = ydh.ego_network(agent_id=5)
            print(f"Agent 5's ego network has {ego_net.number_of_nodes()} nodes")
            print(f"Edges: {ego_net.number_of_edges()}")

            # Analyze network structure
            in_degree = ego_net.in_degree(5)  # Number of followers
            out_degree = ego_net.out_degree(5)  # Number following
            print(f"Followers: {in_degree}, Following: {out_degree}")

            # Get ego network for specific time period
            period_net = ydh.ego_network(agent_id=5, from_round=100, to_round=500)

        See Also:
            :meth:`ego_network_follower`: Get only follower connections
            :meth:`ego_network_following`: Get only following connections
            :meth:`social_network`: Get complete social network for all agents
        """
        following = self.ego_network_following(agent_id, from_round, to_round)
        follower = self.ego_network_follower(agent_id, from_round, to_round)

        g = nx.compose(following, follower)

        return g

    @_handle_db_connection
    def social_network(self, from_round=None, to_round=None, agent_ids=None):
        """
        Extract the complete social network from the simulation.

        Builds a directed graph representing the follow relationships between
        all agents (or a specified subset). Each agent's ego network is extracted
        and then merged into a single comprehensive social network.

        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :param agent_ids: List of agent IDs to include. If None, all agents are included
        :type agent_ids: list[int], optional
        :return: Directed graph representing the complete social network
        :rtype: networkx.DiGraph

        Example::

            import networkx as nx
            from ysights import YDataHandler
            import matplotlib.pyplot as plt

            ydh = YDataHandler('path/to/database.db')

            # Get complete social network
            social_net = ydh.social_network()
            print(f"Social network: {social_net.number_of_nodes()} nodes, {social_net.number_of_edges()} edges")

            # Analyze network properties
            density = nx.density(social_net)
            print(f"Network density: {density:.4f}")

            # Get network for specific agents
            agent_subset = [1, 2, 3, 5, 8, 13, 21]
            subnet = ydh.social_network(agent_ids=agent_subset)

            # Get network for specific time period
            early_net = ydh.social_network(from_round=0, to_round=500)
            late_net = ydh.social_network(from_round=500, to_round=1000)

            # Compare network evolution
            print(f"Early network: {early_net.number_of_edges()} edges")
            print(f"Late network: {late_net.number_of_edges()} edges")

        Warning:
            Extracting the complete social network for all agents can be slow
            for large simulations. Consider using the agent_ids parameter to
            limit the scope or using time range filtering.

        See Also:
            :meth:`ego_network`: Get ego network for single agent
            :meth:`mention_network`: Get mention-based interaction network
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

    @_handle_db_connection
    def mention_ego_network(self, agent_id, from_round=None, to_round=None):
        """
        Extract the mention ego network for a specific agent.

        Returns a directed weighted network showing which agents the specified
        agent has mentioned in their posts. Edge weights represent the number
        of times each agent was mentioned.

        :param agent_id: The ID of the agent (the "ego")
        :type agent_id: int
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Directed weighted graph with edges from ego to mentioned agents
        :rtype: networkx.DiGraph

        Example::

            import networkx as nx
            from ysights import YDataHandler

            ydh = YDataHandler('path/to/database.db')

            # Get mention network for agent 5
            mention_net = ydh.mention_ego_network(agent_id=5)
            print(f"Agent 5 has mentioned {mention_net.number_of_nodes() - 1} different agents")

            # Analyze mention patterns
            for target in mention_net.successors(5):
                weight = mention_net[5][target]['weight']
                print(f"  Mentioned agent {target}: {weight} times")

            # Compare mention patterns over time
            early_mentions = ydh.mention_ego_network(agent_id=5, from_round=0, to_round=500)
            late_mentions = ydh.mention_ego_network(agent_id=5, from_round=500, to_round=1000)

        See Also:
            :meth:`mention_network`: Get complete mention network for all agents
            :meth:`ego_network`: Get follower/following network
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

    @_handle_db_connection
    def mention_network(self, from_round=None, to_round=None, agent_ids=None):
        """
        Extract the complete mention network from the simulation.

        Builds a directed weighted graph representing mention relationships between
        all agents (or a specified subset). Edges indicate one agent mentioning
        another in their posts, with weights showing mention frequency.

        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :param agent_ids: List of agent IDs to include. If None, all agents are included
        :type agent_ids: list[int], optional
        :return: Directed weighted graph representing the mention network
        :rtype: networkx.DiGraph

        Example::

            import networkx as nx
            from ysights import YDataHandler

            ydh = YDataHandler('path/to/database.db')

            # Get complete mention network
            mention_net = ydh.mention_network()
            print(f"Mention network: {mention_net.number_of_nodes()} nodes, {mention_net.number_of_edges()} edges")

            # Find most mentioned agents
            in_degrees = dict(mention_net.in_degree(weight='weight'))
            top_mentioned = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
            print("Most mentioned agents:")
            for agent_id, mention_count in top_mentioned:
                print(f"  Agent {agent_id}: mentioned {mention_count} times")

            # Get mention network for subset
            agent_subset = [1, 2, 3, 5, 8]
            subnet = ydh.mention_network(agent_ids=agent_subset)

            # Compare mention patterns over time
            early = ydh.mention_network(from_round=0, to_round=500)
            late = ydh.mention_network(from_round=500, to_round=1000)

        Warning:
            Extracting the complete mention network for all agents can be slow
            for large simulations. Consider using the agent_ids parameter or
            time range filtering.

        See Also:
            :meth:`mention_ego_network`: Get mention network for single agent
            :meth:`social_network`: Get follower/following network
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
