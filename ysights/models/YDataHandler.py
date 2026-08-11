import os
import sqlite3
from collections import Counter, defaultdict, namedtuple
from functools import wraps
from statistics import median
from urllib.parse import urlparse

import networkx as nx

from ysights.models.Agents import Agent, Agents
from ysights.models.Posts import Post, Posts
from ysights.models.schema import ExperimentSchema

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
            agent_id = next(iter(ydh.agent_mapping()))
            agent_posts = ydh.posts_by_agent(agent_id=agent_id, enrich_dimensions=['sentiment', 'hashtags'])
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

        Entity identifiers are treated as opaque values. Depending on the
        backing database, IDs can be integers, strings, or UUID-like tokens;
        the API does not require numeric arithmetic on identifiers.

    See Also:
        :class:`ysights.models.Agents.Agents`: Container for agent collections
        :class:`ysights.models.Posts.Posts`: Container for post collections
    """

    def __init__(self, db_path):
        """
        Initialize the YDataHandler with database connection information.

        :param db_path: Path to a SQLite database file or a PostgreSQL connection string.
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
        self._schema_cache = None
        self._analysis_cache = {}

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

    def __cache_key(self, name, *args, **kwargs):
        """
        Build a stable cache key for derived analytics.
        """
        return (
            name,
            tuple(args),
            tuple(sorted(kwargs.items())),
        )

    def __analysis_cache_get(self, name, *args, **kwargs):
        return self._analysis_cache.get(self.__cache_key(name, *args, **kwargs))

    def __analysis_cache_set(self, value, name, *args, **kwargs):
        self._analysis_cache[self.__cache_key(name, *args, **kwargs)] = value
        return value

    def __analysis_cache_info(self):
        """
        Inspect the current derived-data cache.
        """
        return {
            "entry_count": len(self._analysis_cache),
            "keys": [key[0] for key in self._analysis_cache.keys()],
        }

    @_handle_db_connection
    def clear_analysis_cache(self):
        """
        Clear cached derived analytics.
        """
        self._analysis_cache.clear()
        return True

    @_handle_db_connection
    def analysis_cache_info(self):
        """
        Report cache usage for derived analytics.
        """
        return self.__analysis_cache_info()

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

        rows, _ = self.__execute_query_with_columns(query, params)
        return rows

    def __execute_query_with_columns(self, query, params=None):
        """
        Execute an SQL query and return rows plus column names.

        :param query: SQL query string to execute
        :type query: str
        :param params: Optional parameters for parameterized queries
        :type params: tuple or list, optional
        :return: Tuple of (rows, columns)
        :rtype: tuple[list, list[str]]
        """
        if not self.connection:
            raise FileNotFoundError("Database connection is not established.")

        query, params = self.__convert_query_for_db(query, params)
        cursor = self.connection.cursor()
        cursor.execute(query, params or [])
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return rows, columns

    def __introspect_schema(self):
        """
        Introspect the current database connection and cache table metadata.

        :return: Introspected experiment schema
        :rtype: ExperimentSchema
        """
        if self.db_type == "sqlite":
            rows = self.__execute_query(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
            tables = [row[0] for row in rows]
            columns = {}
            cursor = self.connection.cursor()
            for table_name in tables:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns[table_name] = frozenset(row[1] for row in cursor.fetchall())
        else:
            rows = self.__execute_query("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_name
                """)
            tables = [row[0] for row in rows]
            columns = {}
            for table_name in tables:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table_name,),
                )
                columns[table_name] = frozenset(row[0] for row in cursor.fetchall())

        return ExperimentSchema(frozenset(tables), columns)

    def __get_schema(self):
        if self._schema_cache is None:
            self._schema_cache = self.__introspect_schema()
        return self._schema_cache

    def __build_time_filter(self, from_round=None, to_round=None, field_name="round"):
        """
        Build a SQL time filter clause and matching parameters.

        :param from_round: Optional lower bound, inclusive.
        :param to_round: Optional upper bound, inclusive.
        :param field_name: SQL field or expression to compare against.
        :return: Tuple of (clause string, parameters tuple).
        """
        clauses = []
        params = []

        if from_round is not None:
            clauses.append(f"{field_name} >= ?")
            params.append(from_round)

        if to_round is not None:
            clauses.append(f"{field_name} <= ?")
            params.append(to_round)

        if not clauses:
            return "", ()

        return " AND " + " AND ".join(clauses), tuple(params)

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

    @_handle_db_connection
    def schema(self):
        """
        Introspect the active dataset schema.

        :return: Cached schema adapter for the connected dataset
        :rtype: ExperimentSchema
        """
        return self.__get_schema()

    @_handle_db_connection
    def capabilities(self):
        """
        Return detected dataset capabilities.

        :return: Dictionary describing available tables, columns, and features
        :rtype: dict
        """
        return self.__get_schema().describe()

    @_handle_db_connection
    def has_table(self, *table_names):
        """
        Check whether any of the named tables is present.

        :param table_names: One or more table names or aliases
        :return: True when one of the tables exists
        :rtype: bool
        """
        return self.__get_schema().has_table(*table_names)

    @_handle_db_connection
    def supports_feature(self, feature_name):
        """
        Check whether a logical experiment feature is supported.

        :param feature_name: Canonical feature name
        :return: True when the feature is available
        :rtype: bool
        """
        return self.__get_schema().supports_feature(feature_name)

    @_handle_db_connection
    def table_frame(self, table_name, columns=None):
        """
        Extract a table as a pandas DataFrame.

        :param table_name: Table name or alias
        :param columns: Optional iterable of column names to project
        :return: DataFrame containing the table rows
        :rtype: pandas.DataFrame
        """
        import pandas as pd

        schema = self.__get_schema()
        resolved_table = schema.resolve_table(table_name)
        select_clause = "*" if columns is None else ", ".join(columns)
        rows, row_columns = self.__execute_query_with_columns(
            f"SELECT {select_clause} FROM {resolved_table}"
        )
        return pd.DataFrame(
            rows, columns=row_columns if columns is None else list(columns)
        )

    def users_frame(self, columns=None):
        return self.table_frame("user_mgmt", columns=columns)

    def posts_frame(self, columns=None):
        return self.table_frame("post", columns=columns)

    def interactions_frame(self, table_name="follow", columns=None):
        return self.table_frame(table_name, columns=columns)

    def forum_messages_frame(self, columns=None):
        return self.table_frame("forum_messages", columns=columns)

    def forum_sessions_frame(self, columns=None):
        return self.table_frame("forum_sessions", columns=columns)

    def __resolve_thread_reference(self, thread_ref):
        """
        Resolve a thread reference to the canonical thread identifier used in the post table.

        The reference can be either a root post id or an existing thread_id value.
        """
        rows = self.__execute_query(
            "SELECT id, thread_id FROM post WHERE id = ?", (thread_ref,)
        )
        if rows:
            post_id, thread_id = rows[0]
            if thread_id not in (None, -1):
                return thread_id
            return post_id

        rows = self.__execute_query(
            "SELECT thread_id FROM post WHERE thread_id = ? LIMIT 1", (thread_ref,)
        )
        if rows:
            return thread_ref

        raise ValueError(
            f"Thread reference {thread_ref} does not exist in the database."
        )

    def __thread_rows(self, thread_ref, from_round=None, to_round=None):
        canonical_thread_id = self.__resolve_thread_reference(thread_ref)
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            "SELECT * FROM post "
            "WHERE (thread_id = ? OR id = ?)"
            f"{time_filter} "
            "ORDER BY round ASC, id ASC"
        )
        rows = self.__execute_query(
            query, (canonical_thread_id, canonical_thread_id, *time_params)
        )
        return canonical_thread_id, rows

    def __posts_from_rows(self, rows):
        posts = Posts()
        for row in rows:
            posts.add_post(Post(row))
        return posts

    def __thread_graph_from_posts(self, posts):
        g = nx.DiGraph()
        post_ids = {post.id for post in posts}

        for post in posts:
            g.add_node(
                post.id,
                user_id=post.user_id,
                round=post.round,
                thread_id=post.thread_id,
                comment_to=post.comment_to,
                text=post.text,
            )

        for post in posts:
            parent_id = post.comment_to
            if parent_id in (None, -1):
                continue
            if parent_id in post_ids:
                g.add_edge(parent_id, post.id)

        return g

    def __thread_metrics_from_posts(self, canonical_thread_id, posts):
        if not posts:
            return {
                "thread_id": canonical_thread_id,
                "root_post_id": None,
                "post_count": 0,
                "reply_count": 0,
                "participant_count": 0,
                "max_depth": 0,
                "branching_factor": 0.0,
                "average_reply_latency": 0.0,
                "median_reply_latency": 0.0,
                "thread_span_rounds": 0,
                "root_reply_count": 0,
                "root_reply_share": 0.0,
                "cascade_size": 0,
                "average_depth": 0.0,
                "root_user_id": None,
            }

        graph = self.__thread_graph_from_posts(posts)
        post_map = {post.id: post for post in posts}
        root_candidates = [
            post.id
            for post in posts
            if post.comment_to in (None, -1) or post.comment_to not in post_map
        ]
        if not root_candidates:
            root_candidates = [posts[0].id]
        root_post_id = min(root_candidates, key=lambda pid: post_map[pid].round)
        root_post = post_map[root_post_id]

        participants = {post.user_id for post in posts}
        reply_latencies = [
            post_map[child_id].round - post_map[parent_id].round
            for parent_id, child_id in graph.edges()
        ]

        depths = {}
        for node in graph.nodes():
            try:
                depths[node] = nx.shortest_path_length(
                    graph, source=root_post_id, target=node
                )
            except nx.NetworkXNoPath:
                depths[node] = 0

        non_leaf_nodes = [node for node in graph.nodes() if graph.out_degree(node) > 0]
        branching_factor = (
            sum(graph.out_degree(node) for node in non_leaf_nodes) / len(non_leaf_nodes)
            if non_leaf_nodes
            else 0.0
        )

        root_reply_count = graph.out_degree(root_post_id)
        reply_count = graph.number_of_edges()
        rounds = [post.round for post in posts]

        metrics = {
            "thread_id": canonical_thread_id,
            "root_post_id": root_post_id,
            "post_count": len(posts),
            "reply_count": reply_count,
            "participant_count": len(participants),
            "max_depth": max(depths.values()) if depths else 0,
            "average_depth": sum(depths.values()) / len(depths) if depths else 0.0,
            "branching_factor": branching_factor,
            "average_reply_latency": (
                sum(reply_latencies) / len(reply_latencies) if reply_latencies else 0.0
            ),
            "median_reply_latency": (
                float(median(reply_latencies)) if reply_latencies else 0.0
            ),
            "thread_span_rounds": max(rounds) - min(rounds),
            "root_reply_count": root_reply_count,
            "root_reply_share": root_reply_count / reply_count if reply_count else 0.0,
            "cascade_size": len(posts),
            "root_user_id": root_post.user_id,
        }
        return metrics

    @_handle_db_connection
    def thread_ids(self, from_round=None, to_round=None):
        """
        Return the canonical thread identifiers available in the dataset.

        :return: List of canonical thread identifiers
        :rtype: list
        """
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            "SELECT DISTINCT CASE WHEN p.thread_id IS NULL OR p.thread_id = -1 THEN p.id ELSE p.thread_id END AS thread_ref "
            "FROM post AS p"
            f"{time_filter} "
            "ORDER BY thread_ref ASC"
        )
        rows = self.__execute_query(query, time_params)
        return [row[0] for row in rows]

    @_handle_db_connection
    def thread_posts(self, thread_ref, from_round=None, to_round=None):
        """
        Retrieve all posts that belong to a thread.

        :param thread_ref: Thread id or root post id
        :return: Posts collection ordered by round and id
        :rtype: Posts
        """
        _, rows = self.__thread_rows(thread_ref, from_round, to_round)
        return self.__posts_from_rows(rows)

    @_handle_db_connection
    def thread_graph(self, thread_ref, from_round=None, to_round=None):
        """
        Reconstruct a conversation tree for a thread.

        Nodes are posts; directed edges point from parent post to reply post.
        """
        _, rows = self.__thread_rows(thread_ref, from_round, to_round)
        posts = self.__posts_from_rows(rows).get_posts()
        return self.__thread_graph_from_posts(posts)

    conversation_graph = thread_graph

    @_handle_db_connection
    def thread_metrics(self, thread_ref, from_round=None, to_round=None):
        """
        Compute conversation metrics for a thread.

        Metrics include:
        - post_count
        - reply_count
        - participant_count
        - max_depth
        - branching_factor
        - average_reply_latency
        - median_reply_latency
        - thread_span_rounds
        - root_post_id
        - root_reply_count
        - root_reply_share
        - cascade_size
        """
        canonical_thread_id, rows = self.__thread_rows(thread_ref, from_round, to_round)
        posts = self.__posts_from_rows(rows).get_posts()
        return self.__thread_metrics_from_posts(canonical_thread_id, posts)

    @_handle_db_connection
    def thread_summaries(self, from_round=None, to_round=None):
        """
        Return conversation metrics for all threads in the dataset.

        :return: Mapping of thread identifier to metrics dictionary
        :rtype: dict
        """
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            "SELECT DISTINCT CASE WHEN p.thread_id IS NULL OR p.thread_id = -1 THEN p.id ELSE p.thread_id END AS thread_ref "
            "FROM post AS p"
            f"{time_filter} "
            "ORDER BY thread_ref ASC"
        )
        rows = self.__execute_query(query, time_params)
        summaries = {}
        for row in rows:
            thread_ref = row[0]
            _, thread_rows = self.__thread_rows(thread_ref, from_round, to_round)
            posts = self.__posts_from_rows(thread_rows).get_posts()
            summaries[thread_ref] = self.__thread_metrics_from_posts(thread_ref, posts)
        return summaries

    def __period_clause(self, alias, round_column, granularity):
        """
        Build a grouping expression for round- or day-level timelines.
        """
        granularity = granularity.lower()
        if granularity == "round":
            return f"{alias}.{round_column}", ""

        if granularity == "day":
            if self.__get_schema().has_table("rounds"):
                return "rd.day", f" JOIN rounds AS rd ON {alias}.{round_column} = rd.id"
            return f"{alias}.{round_column}", ""

        raise ValueError("granularity must be 'round' or 'day'")

    def __single_metric_timeline(
        self,
        table_name,
        alias,
        round_column,
        metric_name,
        from_round=None,
        to_round=None,
        granularity="round",
        extra_join="",
        extra_where="",
    ):
        """
        Build a simple timeline with one metric per period.
        """
        period_expr, period_join = self.__period_clause(
            alias, round_column, granularity
        )
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, f"{alias}.{round_column}"
        )
        query = (
            f"SELECT {period_expr} AS period, COUNT(*) AS {metric_name} "
            f"FROM {table_name} AS {alias}"
            f"{period_join}"
            f"{extra_join}"
            f" WHERE 1=1{extra_where}{time_filter} "
            f"GROUP BY period ORDER BY period ASC"
        )
        rows = self.__execute_query(query, time_params)
        import pandas as pd

        return pd.DataFrame(rows, columns=["period", metric_name])

    def __activity_timeline_frame(
        self, granularity="round", from_round=None, to_round=None
    ):
        """
        Build a multi-metric activity timeline for posts and interactions.

        :return: DataFrame with counts for posts, replies, reactions, recommendations, mentions, and authors
        :rtype: pandas.DataFrame
        """
        import pandas as pd

        period_expr, period_join = self.__period_clause("p", "round", granularity)
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        post_query = (
            f"SELECT {period_expr} AS period, "
            "COUNT(*) AS posts, "
            "SUM(CASE WHEN p.comment_to IS NOT NULL AND p.comment_to != -1 THEN 1 ELSE 0 END) AS replies, "
            "COUNT(DISTINCT p.user_id) AS authors "
            "FROM post AS p"
            f"{period_join}"
            f" WHERE 1=1{time_filter} "
            "GROUP BY period ORDER BY period ASC"
        )
        posts_df = pd.DataFrame(
            self.__execute_query(post_query, time_params),
            columns=["period", "posts", "replies", "authors"],
        )

        frames = [posts_df]
        schema = self.__get_schema()
        if schema.has_table("reactions"):
            frames.append(
                self.__single_metric_timeline(
                    "reactions",
                    "x",
                    "round",
                    "reactions",
                    from_round=from_round,
                    to_round=to_round,
                    granularity=granularity,
                )
            )
        if schema.has_table("recommendations"):
            frames.append(
                self.__single_metric_timeline(
                    "recommendations",
                    "x",
                    "round",
                    "recommendations",
                    from_round=from_round,
                    to_round=to_round,
                    granularity=granularity,
                )
            )
        if schema.has_table("mentions"):
            frames.append(
                self.__single_metric_timeline(
                    "mentions",
                    "x",
                    "round",
                    "mentions",
                    from_round=from_round,
                    to_round=to_round,
                    granularity=granularity,
                )
            )

        timeline = posts_df
        for frame in frames[1:]:
            timeline = timeline.merge(frame, on="period", how="outer")

        timeline = timeline.fillna(0).sort_values("period").reset_index(drop=True)
        numeric_columns = [col for col in timeline.columns if col != "period"]
        for column in numeric_columns:
            timeline[column] = timeline[column].astype(int)
        return timeline

    @_handle_db_connection
    def activity_timeline(self, granularity="round", from_round=None, to_round=None):
        return self.__activity_timeline_frame(
            granularity=granularity, from_round=from_round, to_round=to_round
        )

    @_handle_db_connection
    def burst_windows(
        self,
        metric="posts",
        granularity="round",
        window_size=3,
        z_threshold=2.0,
        from_round=None,
        to_round=None,
    ):
        """
        Detect bursts in an activity timeline using rolling z-scores.
        """
        import pandas as pd

        timeline = self.__activity_timeline_frame(
            granularity=granularity, from_round=from_round, to_round=to_round
        )
        if timeline.empty:
            return timeline
        if metric not in timeline.columns:
            raise KeyError(f"Metric '{metric}' is not available in the timeline.")

        series = timeline[metric].astype(float)
        rolling_mean = series.rolling(window=window_size, min_periods=1).mean()
        rolling_std = series.rolling(window=window_size, min_periods=1).std(ddof=0)
        safe_std = rolling_std.where(rolling_std != 0, float("nan"))
        z_scores = ((series - rolling_mean) / safe_std).fillna(0.0)

        result = timeline.copy()
        result["rolling_mean"] = rolling_mean
        result["rolling_std"] = rolling_std.fillna(0.0).astype(float)
        result["z_score"] = z_scores
        result["is_burst"] = result["z_score"] >= z_threshold
        return result

    @_handle_db_connection
    def compare_time_windows(
        self,
        metric="posts",
        window_a=None,
        window_b=None,
        granularity="round",
    ):
        """
        Compare a metric across two windows.

        :param window_a: Tuple of (from_round, to_round)
        :param window_b: Tuple of (from_round, to_round)
        """
        if window_a is None or window_b is None:
            raise ValueError("window_a and window_b are required.")

        timeline_a = self.__activity_timeline_frame(
            granularity=granularity, from_round=window_a[0], to_round=window_a[1]
        )
        timeline_b = self.__activity_timeline_frame(
            granularity=granularity, from_round=window_b[0], to_round=window_b[1]
        )
        if metric not in timeline_a.columns or metric not in timeline_b.columns:
            raise KeyError(f"Metric '{metric}' is not available in the timeline.")

        value_a = int(timeline_a[metric].sum())
        value_b = int(timeline_b[metric].sum())
        delta = value_b - value_a
        relative_change = (delta / value_a) if value_a else None

        return {
            "metric": metric,
            "granularity": granularity,
            "window_a": {
                "from_round": window_a[0],
                "to_round": window_a[1],
                "value": value_a,
            },
            "window_b": {
                "from_round": window_b[0],
                "to_round": window_b[1],
                "value": value_b,
            },
            "delta": delta,
            "relative_change": relative_change,
        }

    @_handle_db_connection
    def topic_timeline(
        self, topic_id, granularity="round", from_round=None, to_round=None
    ):
        """
        Track the growth of a topic over time.
        """
        timeline = self.__topic_activity_frame(
            topic_id,
            granularity=granularity,
            from_round=from_round,
            to_round=to_round,
        )
        if timeline.empty:
            return timeline
        return timeline[["period", "posts"]]

    def __topic_activity_frame(
        self, topic_id, granularity="round", from_round=None, to_round=None
    ):
        """
        Build a topic timeline enriched with author counts.
        """
        if not self.__get_schema().supports_feature("topics"):
            raise ValueError("Topic analysis is not available in this dataset.")

        import pandas as pd

        period_expr, period_join = self.__period_clause("p", "round", granularity)
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            f"SELECT {period_expr} AS period, "
            "COUNT(DISTINCT p.id) AS posts, "
            "COUNT(DISTINCT p.user_id) AS authors "
            "FROM post_topics AS pt "
            "JOIN post AS p ON p.id = pt.post_id"
            f"{period_join}"
            f" WHERE pt.topic_id = ?{time_filter} "
            "GROUP BY period ORDER BY period ASC"
        )
        rows = self.__execute_query(query, (topic_id, *time_params))
        return pd.DataFrame(rows, columns=["period", "posts", "authors"])

    @_handle_db_connection
    def topic_lifecycle(
        self, topic_id, granularity="round", from_round=None, to_round=None
    ):
        """
        Summarize the lifecycle of a topic.
        """
        cached = self.__analysis_cache_get(
            "topic_lifecycle",
            topic_id,
            granularity=granularity,
            from_round=from_round,
            to_round=to_round,
        )
        if cached is not None:
            return cached

        timeline = self.__topic_activity_frame(
            topic_id,
            granularity=granularity,
            from_round=from_round,
            to_round=to_round,
        )
        if timeline.empty:
            result = {
                "topic_id": topic_id,
                "granularity": granularity,
                "timeline": timeline,
                "post_count": 0,
                "author_count": 0,
                "period_count": 0,
                "first_period": None,
                "last_period": None,
                "peak_period": None,
                "peak_posts": 0,
                "peak_share": 0.0,
                "adoption_rate": 0.0,
                "half_life_period": None,
            }
            return self.__analysis_cache_set(
                result,
                "topic_lifecycle",
                topic_id,
                granularity=granularity,
                from_round=from_round,
                to_round=to_round,
            )

        timeline = timeline.copy()
        timeline["cumulative_posts"] = timeline["posts"].cumsum()
        timeline["cumulative_authors"] = timeline["authors"].cumsum()

        total_posts = int(timeline["posts"].sum())
        author_query = (
            "SELECT COUNT(DISTINCT p.user_id) "
            "FROM post_topics AS pt "
            "JOIN post AS p ON p.id = pt.post_id "
            "WHERE pt.topic_id = ?"
        )
        author_rows = self.__execute_query(author_query, (topic_id,))
        total_authors = int(author_rows[0][0]) if author_rows else 0
        first_period = timeline.iloc[0]["period"]
        last_period = timeline.iloc[-1]["period"]
        peak_index = timeline["posts"].idxmax()
        peak_period = timeline.loc[peak_index, "period"]
        peak_posts = int(timeline.loc[peak_index, "posts"])
        peak_share = (peak_posts / total_posts) if total_posts else 0.0
        period_count = int(len(timeline))
        adoption_rate = (total_posts / period_count) if period_count else 0.0
        half_life_threshold = total_posts / 2.0 if total_posts else 0.0
        half_life_period = None
        for _, row in timeline.iterrows():
            if row["cumulative_posts"] >= half_life_threshold:
                half_life_period = row["period"]
                break

        result = {
            "topic_id": topic_id,
            "granularity": granularity,
            "timeline": timeline,
            "post_count": total_posts,
            "author_count": total_authors,
            "period_count": period_count,
            "first_period": first_period,
            "last_period": last_period,
            "peak_period": peak_period,
            "peak_posts": peak_posts,
            "peak_share": peak_share,
            "adoption_rate": adoption_rate,
            "half_life_period": half_life_period,
        }
        return self.__analysis_cache_set(
            result,
            "topic_lifecycle",
            topic_id,
            granularity=granularity,
            from_round=from_round,
            to_round=to_round,
        )

    def normalize_text(
        self,
        text,
        lower=True,
        strip_urls=True,
        strip_hashtags=False,
        strip_mentions=False,
    ):
        """
        Normalize free text for semantic analysis.
        """
        import re
        import string

        text = text or ""
        urls = re.findall(r"https?://\S+|www\.\S+", text)
        working = text
        if strip_urls and urls:
            working = re.sub(r"https?://\S+|www\.\S+", " ", working)

        if lower:
            working = working.lower()

        hashtag_tokens = re.findall(r"#\w+(?:'\w+)?", working)
        mention_tokens = re.findall(r"@\w+(?:'\w+)?", working)

        if strip_hashtags:
            working = re.sub(r"#\w+(?:'\w+)?", " ", working)
        if strip_mentions:
            working = re.sub(r"@\w+(?:'\w+)?", " ", working)

        punctuation_count = sum(1 for ch in working if ch in string.punctuation)
        translation = str.maketrans({ch: " " for ch in string.punctuation})
        normalized_text = re.sub(r"\s+", " ", working.translate(translation)).strip()
        tokens = re.findall(r"\w+(?:'\w+)?", normalized_text)

        return {
            "original_text": text,
            "normalized_text": normalized_text,
            "tokens": tokens,
            "url_count": len(urls),
            "hashtag_count": len(hashtag_tokens),
            "mention_count": len(mention_tokens),
            "punctuation_count": punctuation_count,
            "duplicate_token_count": max(len(tokens) - len(set(tokens)), 0),
        }

    def text_semantic_profile(self, text):
        """
        Extract lightweight semantic features from a text string.
        """
        import math
        import re
        from collections import Counter

        normalized = self.normalize_text(text)
        raw_text = normalized["original_text"]
        tokens = normalized["tokens"]
        words = [
            token
            for token in tokens
            if not token.startswith("#") and not token.startswith("@")
        ]
        lower_word_counts = Counter(word.lower() for word in words)
        alpha_chars = [ch for ch in raw_text if ch.isalpha()]
        upper_chars = [ch for ch in alpha_chars if ch.isupper()]
        word_lengths = [len(word) for word in words]
        avg_word_length = (
            (sum(word_lengths) / len(word_lengths)) if word_lengths else 0.0
        )
        unique_words = {word.lower() for word in words}
        sentences = [
            sentence.strip()
            for sentence in re.split(r"[.!?]+", raw_text)
            if sentence.strip()
        ]
        sentence_lengths = [
            len(self.normalize_text(sentence)["tokens"]) for sentence in sentences
        ]
        avg_sentence_length = (
            (sum(sentence_lengths) / len(sentence_lengths)) if sentence_lengths else 0.0
        )
        readability_proxy = 100.0 - (avg_sentence_length * 1.5) - (avg_word_length * 2.0)
        lexical_diversity = (len(unique_words) / len(words)) if words else 0.0
        duplicate_token_ratio = (
            normalized["duplicate_token_count"] / len(tokens) if tokens else 0.0
        )

        return {
            "character_count": len(raw_text),
            "normalized_character_count": len(normalized["normalized_text"]),
            "token_count": len(tokens),
            "word_count": len(words),
            "unique_word_count": len(unique_words),
            "lexical_diversity": lexical_diversity,
            "type_token_ratio": lexical_diversity,
            "avg_word_length": avg_word_length,
            "url_count": normalized["url_count"],
            "hashtag_count": normalized["hashtag_count"],
            "mention_count": normalized["mention_count"],
            "punctuation_count": normalized["punctuation_count"],
            "punctuation_ratio": (
                normalized["punctuation_count"] / len(raw_text) if raw_text else 0.0
            ),
            "punctuation_intensity": (
                normalized["punctuation_count"] / max(len(tokens), 1)
                if raw_text
                else 0.0
            ),
            "uppercase_ratio": (
                (len(upper_chars) / len(alpha_chars)) if alpha_chars else 0.0
            ),
            "digit_count": sum(ch.isdigit() for ch in raw_text),
            "sentence_count": len(sentences),
            "avg_sentence_length": avg_sentence_length,
            "readability_proxy": readability_proxy,
            "duplicate_token_count": normalized["duplicate_token_count"],
            "duplicate_token_ratio": duplicate_token_ratio,
            "entropy_proxy": (
                -sum(
                    (count / len(words)) * math.log(count / len(words), 2)
                    for count in lower_word_counts.values()
                )
                if words
                else 0.0
            ),
        }

    def __text_profile(self, text):
        """
        Backward-compatible internal alias for text semantic profiling.
        """
        return self.text_semantic_profile(text)

    @_handle_db_connection
    def post_semantic_profile(self, post_id):
        """
        Extract semantic surface features for a microblog post.
        """
        cached = self.__analysis_cache_get("post_semantic_profile", post_id)
        if cached is not None:
            return cached

        query = "SELECT tweet FROM post WHERE id = ?"
        data = self.__execute_query(query, (post_id,))
        if not data:
            raise ValueError(f"Post ID {post_id} does not exist in the database.")
        return self.__analysis_cache_set(
            self.text_semantic_profile(data[0][0]), "post_semantic_profile", post_id
        )

    @_handle_db_connection
    def forum_message_semantic_profile(self, message_id):
        """
        Extract semantic surface features for a forum message.
        """
        cached = self.__analysis_cache_get("forum_message_semantic_profile", message_id)
        if cached is not None:
            return cached

        schema = self.__get_schema()
        table_name = schema.resolve_table("forum_messages")
        if schema.has_column(table_name, "content"):
            column_name = "content"
        elif schema.has_column(table_name, "message"):
            column_name = "message"
        else:
            raise ValueError("Forum message text column was not found in this dataset.")

        query = f"SELECT {column_name} FROM {table_name} WHERE id = ?"
        data = self.__execute_query(query, (message_id,))
        if not data:
            raise ValueError(
                f"Forum message ID {message_id} does not exist in the database."
            )
        return self.__analysis_cache_set(
            self.text_semantic_profile(data[0][0]),
            "forum_message_semantic_profile",
            message_id,
        )

    def semantic_similarity(self, text_a, text_b, use_embeddings=False, model_name=None):
        """
        Compare two text snippets using lexical similarity or optional embeddings.
        """
        import math
        from collections import Counter

        text_a = text_a or ""
        text_b = text_b or ""

        if use_embeddings:
            try:
                import numpy as np
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(model_name or "all-MiniLM-L6-v2")
                vectors = model.encode([text_a, text_b], normalize_embeddings=True)
                score = float(np.dot(vectors[0], vectors[1]))
                return {
                    "mode": "embedding",
                    "model": model_name or "all-MiniLM-L6-v2",
                    "score": score,
                }
            except Exception:
                pass

        profile_a = self.text_semantic_profile(text_a)
        profile_b = self.text_semantic_profile(text_b)
        tokens_a = Counter(self.normalize_text(text_a)["tokens"])
        tokens_b = Counter(self.normalize_text(text_b)["tokens"])

        shared_tokens = set(tokens_a) & set(tokens_b)
        dot = sum(tokens_a[token] * tokens_b[token] for token in shared_tokens)
        norm_a = math.sqrt(sum(value * value for value in tokens_a.values()))
        norm_b = math.sqrt(sum(value * value for value in tokens_b.values()))
        lexical_cosine = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
        token_union = set(tokens_a) | set(tokens_b)
        token_jaccard = (
            len(shared_tokens) / len(token_union) if token_union else 0.0
        )

        return {
            "mode": "lexical",
            "score": lexical_cosine,
            "lexical_cosine": lexical_cosine,
            "token_jaccard": token_jaccard,
            "shared_token_count": len(shared_tokens),
            "text_a_profile": profile_a,
            "text_b_profile": profile_b,
        }

    # Time
    @_handle_db_connection
    def time_range(self):
        """
        Retrieve the time range covered by the simulation.

        Returns the minimum and maximum round IDs present in the database,
        representing the temporal extent of the simulation data. Uses day and hour
        fields to determine the earliest and latest rounds (not round IDs which may
        be non-sequential UUIDs).

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
        # Find the earliest round (minimum day, and minimum hour for that day)
        query_min_day = "SELECT MIN(day) FROM rounds"
        data = self.__execute_query(query_min_day)
        if not data or data[0][0] is None:
            raise ValueError("No rounds found in the database.")

        min_day = data[0][0]
        query_min_round = (
            "SELECT id FROM rounds WHERE day = ? ORDER BY hour ASC LIMIT 1"
        )
        data = self.__execute_query(query_min_round, (min_day,))
        if not data:
            raise ValueError("No rounds found in the database.")
        min_round = data[0][0]

        # Find the latest round (maximum day, and maximum hour for that day)
        query_max_day = "SELECT MAX(day) FROM rounds"
        data = self.__execute_query(query_max_day)
        max_day = data[0][0]
        query_max_round = (
            "SELECT id FROM rounds WHERE day = ? ORDER BY hour DESC LIMIT 1"
        )
        data = self.__execute_query(query_max_round, (max_day,))
        if not data:
            raise ValueError("No rounds found in the database.")
        max_round = data[0][0]

        return {"min_round": min_round, "max_round": max_round}

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

    @_handle_db_connection
    def get_rounds_in_time_range(self, start_day, start_hour, end_day, end_hour):
        """
        Get all round IDs within a specified time range.

        Returns round IDs for all rounds that fall between the start and end times
        (inclusive), based on day and hour fields. This is useful for filtering
        data by temporal windows when round IDs may not be sequential.

        :param start_day: Starting day (inclusive)
        :type start_day: int
        :param start_hour: Starting hour (inclusive)
        :type start_hour: int
        :param end_day: Ending day (inclusive)
        :type end_day: int
        :param end_hour: Ending hour (inclusive)
        :type end_hour: int
        :return: List of round IDs within the time range
        :rtype: list

        Example::

            ydh = YDataHandler('path/to/database.db')

            # Get all rounds between day 5, hour 10 and day 7, hour 15
            round_ids = ydh.get_rounds_in_time_range(
                start_day=5, start_hour=10,
                end_day=7, end_hour=15
            )
            print(f"Found {len(round_ids)} rounds in time range")

            # Use for filtering posts
            posts_in_range = [p for p in all_posts if p.round in round_ids]

        Note:
            This method correctly handles non-sequential round IDs (e.g., UUIDs)
            by using the day/hour fields for temporal ordering.
        """
        query = """
            SELECT id FROM rounds 
            WHERE (day > ? OR (day = ? AND hour >= ?))
            AND (day < ? OR (day = ? AND hour <= ?))
        """
        data = self.__execute_query(
            query, (start_day, start_day, start_hour, end_day, end_day, end_hour)
        )
        return [row[0] for row in data]

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
            agent_id = next(iter(mapping))
            print(f"Selected agent's username: {mapping[agent_id]}")

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
        :type agent_id: Any
        :return: Dictionary of post identifiers (post_id -> post_id mapping)
        :rtype: dict

        Example::

            ydh = YDataHandler('path/to/database.db')

            post_ids = ydh.agent_post_ids(agent_id=<agent_identifier>)
            print(f"Found {len(post_ids)} posts for the selected agent")
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
        :type agent_id: Any
        :param enrich_dimensions: List of dimensions to enrich. Options:
                                 'sentiment', 'hashtags', 'mentions', 'emotions',
                                 'topics', 'toxicity', 'reactions', 'all', or []
        :type enrich_dimensions: list[str]
        :return: Collection of posts by the specified agent
        :rtype: Posts

        Example::

            ydh = YDataHandler('path/to/database.db')
            agent_id = next(iter(ydh.agent_mapping()))

            # Get posts with full enrichment
            posts = ydh.posts_by_agent(agent_id=agent_id, enrich_dimensions=['all'])
            for post in posts.get_posts():
                print(f"Post: {post.text}")
                print(f"Sentiment: {post.sentiment}")
                print(f"Hashtags: {post.hashtags}")
                print(f"Topics: {post.topics}")

            # Get posts with selective enrichment (faster)
            posts = ydh.posts_by_agent(agent_id=agent_id, enrich_dimensions=['sentiment', 'hashtags'])

            # Get posts without enrichment
            posts = ydh.posts_by_agent(agent_id=agent_id, enrich_dimensions=[])

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
        :type post_id: Any
        :return: The identifier of the agent who created the post
        :rtype: Any
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
        :type agent_id: Any
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping UserPost to recommendation count
        :rtype: dict[UserPost, int]

        Example::

            ydh = YDataHandler('path/to/database.db')
            agent_id = next(iter(ydh.agent_mapping()))

            # Get all recommendations for a selected agent
            recs = ydh.agent_recommendations(agent_id=agent_id)
            print(f"Received {len(recs)} unique post recommendations")

            for user_post, count in recs.items():
                print(f"Post {user_post.post_id} by agent {user_post.agent_id}: {count} times")

            # Get recommendations in specific time range
            recs = ydh.agent_recommendations(agent_id=<agent_identifier>, from_round=100, to_round=200)
            print(f"Recommendations in rounds 100-200: {len(recs)}")

        See Also:
            :meth:`recommendations_per_post`: Get recommendation counts per post
            :meth:`agent_posts_visibility`: Get visibility of agent's own posts
        """
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "r.round"
        )
        query = f"SELECT r.post_ids FROM recommendations as r WHERE user_id = ?{time_filter}"
        data = self.__execute_query(query, (agent_id, *time_params))

        recommendations = defaultdict(int)
        for row in data:
            rw = row[0].split("|")

            for r in rw:
                aid = self.agent_id_by_post_id(r)
                recommendations[UserPost(agent_id=aid, post_id=r)] += 1

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
        :type agent_id: Any
        :param rec_stats: Dictionary of post identifiers to their recommendation counts
                         (typically from recommendations_per_post())
        :type rec_stats: dict
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping post identifiers to recommendation counts
        :rtype: dict

        Example::

            ydh = YDataHandler('path/to/database.db')
            agent_id = next(iter(ydh.agent_mapping()))

            # First get overall recommendation stats
            rec_stats = ydh.recommendations_per_post()

            # Then get visibility for specific agent
            visibility = ydh.agent_posts_visibility(agent_id=agent_id, rec_stats=rec_stats)
            print("Selected agent's post visibility:")
            for post_id, count in visibility.items():
                print(f"  Post {post_id} was recommended {count} times")

            # Get visibility in specific time range
            visibility = ydh.agent_posts_visibility(
                agent_id=agent_id, rec_stats=rec_stats,
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

        posts = {row[0]: None for row in data}

        # filter rec_stats to only include posts made by the agent
        filtered_recs = {k: v for k, v in rec_stats.items() if k in posts}
        return filtered_recs

    @_handle_db_connection
    def recommendations_per_post(self):
        """
        Get recommendation counts for all posts in the simulation.

        Aggregates how many times each post was recommended across all agents
        and all rounds. Useful for identifying popular or viral content.

        :return: Dictionary mapping post identifiers to their total recommendation counts
        :rtype: dict

        Example::

            ydh = YDataHandler('path/to/database.db')

            rec_stats = ydh.recommendations_per_post()

            # Find most recommended posts
            sorted_posts = sorted(rec_stats.items(), key=lambda x: x[1], reverse=True)
            print("Top 10 most recommended posts:")
            for post_id, count in sorted_posts[:10]:
                print(f"  Post {post_id}: {count} recommendations")

            # Use for visibility analysis
            agent_id = next(iter(ydh.agent_mapping()))
            visibility = ydh.agent_posts_visibility(agent_id=agent_id, rec_stats=rec_stats)

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
                rec_stats[r] += 1

        return rec_stats

    @_handle_db_connection
    def recommendations_per_post_per_user(self):
        """
        Get detailed recommendation data including per-user reading history.

        Returns both aggregated recommendation counts per post and a mapping of
        which posts each user received in their recommendations. This provides
        detailed insight into content distribution patterns.

        :return: Tuple of (post_recs, user_to_posts_read) where:
                 - post_recs: dict mapping post identifier to recommendation count
                 - user_to_posts_read: dict mapping user identifier to list of post identifiers they received
        :rtype: tuple[dict, dict]

        Example::

            ydh = YDataHandler('path/to/database.db')

            post_recs, user_reading_history = ydh.recommendations_per_post_per_user()

            # Analyze post popularity
            print("Most recommended posts:")
            for post_id, count in sorted(post_recs.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  Post {post_id}: {count} recommendations")

            # Analyze user reading patterns
            user_id = <user_identifier>
            posts_seen = user_reading_history[user_id]
            print(f"Selected user saw {len(posts_seen)} posts")
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
                user_to_posts_read[uid].append(p)
                if p not in post_recs:
                    post_recs[p] = 1

                else:
                    post_recs[p] += 1

        return post_recs, user_to_posts_read

    @_handle_db_connection
    def recommendation_exposure_summary(self, from_round=None, to_round=None):
        """
        Summarize recommendation exposure, conversion, and feedback-loop signals.

        The summary counts how many recommendation exposures occurred, how often
        those exposures led to reactions, replies, or mentions, and how strongly
        recommendation traffic concentrates on a small set of posts.
        """
        import pandas as pd

        cached = self.__analysis_cache_get(
            "recommendation_exposure_summary",
            from_round=from_round,
            to_round=to_round,
        )
        if cached is not None:
            return cached

        if not self.__get_schema().has_table("recommendations"):
            empty = {
                "available": False,
                "exposure_count": 0,
                "unique_recipients": 0,
                "unique_posts": 0,
                "unique_authors": 0,
                "exposure_by_post": {},
                "exposure_by_recipient": {},
                "conversion_counts": {
                    "reaction": 0,
                    "reply": 0,
                    "mention": 0,
                    "any": 0,
                },
                "conversion_rates": {
                    "reaction": 0.0,
                    "reply": 0.0,
                    "mention": 0.0,
                    "any": 0.0,
                },
                "feedback_loop": {
                    "repeat_pair_exposures": 0,
                    "repeat_pair_rate": 0.0,
                    "top_post_share": 0.0,
                    "top_decile_share": 0.0,
                    "exposure_concentration": 0.0,
                },
                "timeline": pd.DataFrame(
                    columns=[
                        "round",
                        "exposure_count",
                        "reaction_conversions",
                        "reply_conversions",
                        "mention_conversions",
                        "any_conversion",
                    ]
                ),
            }
            return self.__analysis_cache_set(
                empty,
                "recommendation_exposure_summary",
                from_round=from_round,
                to_round=to_round,
            )

        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "r.round"
        )
        recommendation_rows = self.__execute_query(
            (
                "SELECT r.user_id, r.post_ids, r.round "
                "FROM recommendations AS r"
                f" WHERE 1=1{time_filter} "
                "ORDER BY r.round ASC, r.id ASC"
            ),
            time_params,
        )
        if not recommendation_rows:
            return self.__analysis_cache_set(
                {
                    "available": True,
                    "exposure_count": 0,
                    "unique_recipients": 0,
                    "unique_posts": 0,
                    "unique_authors": 0,
                    "exposure_by_post": {},
                    "exposure_by_recipient": {},
                    "conversion_counts": {
                        "reaction": 0,
                        "reply": 0,
                        "mention": 0,
                        "any": 0,
                    },
                    "conversion_rates": {
                        "reaction": 0.0,
                        "reply": 0.0,
                        "mention": 0.0,
                        "any": 0.0,
                    },
                    "feedback_loop": {
                        "repeat_pair_exposures": 0,
                        "repeat_pair_rate": 0.0,
                        "top_post_share": 0.0,
                        "top_decile_share": 0.0,
                        "exposure_concentration": 0.0,
                    },
                    "timeline": pd.DataFrame(
                        columns=[
                            "round",
                            "exposure_count",
                            "reaction_conversions",
                            "reply_conversions",
                            "mention_conversions",
                            "any_conversion",
                        ]
                    ),
                },
                "recommendation_exposure_summary",
                from_round=from_round,
                to_round=to_round,
            )

        post_rows = self.__execute_query("SELECT id, user_id FROM post")
        post_author_by_key = {str(post_id): user_id for post_id, user_id in post_rows}

        reaction_rows = self.__execute_query(
            "SELECT user_id, post_id, round FROM reactions"
            if self.__get_schema().has_table("reactions")
            else "SELECT NULL, NULL, NULL WHERE 1 = 0"
        )
        reply_rows = self.__execute_query(
            "SELECT user_id, comment_to, round FROM post "
            "WHERE comment_to IS NOT NULL AND comment_to != -1"
        )
        mention_rows = self.__execute_query(
            "SELECT p.user_id, m.user_id, p.round "
            "FROM post AS p, mentions AS m "
            "WHERE p.id = m.post_id"
            if self.__get_schema().has_table("mentions")
            else "SELECT NULL, NULL, NULL WHERE 1 = 0"
        )

        reaction_index = defaultdict(list)
        for user_id, post_id, round_id in reaction_rows:
            reaction_index[(user_id, str(post_id))].append(round_id)

        reply_index = defaultdict(list)
        for user_id, comment_to, round_id in reply_rows:
            reply_index[(user_id, str(comment_to))].append(round_id)

        mention_index = defaultdict(list)
        for user_id, mentioned_user_id, round_id in mention_rows:
            mention_index[(user_id, str(mentioned_user_id))].append(round_id)

        exposure_by_post = Counter()
        exposure_by_recipient = Counter()
        exposure_by_pair = Counter()
        timeline_rows = []
        conversion_counts = Counter()

        for user_id, post_ids, exposure_round in recommendation_rows:
            if not post_ids:
                continue
            for post_id in str(post_ids).split("|"):
                post_key = str(post_id).strip()
                if not post_key or post_key not in post_author_by_key:
                    continue
                author_id = post_author_by_key[post_key]
                exposure_by_post[post_key] += 1
                exposure_by_recipient[str(user_id)] += 1
                exposure_by_pair[(str(user_id), post_key)] += 1

                reaction_match = any(
                    action_round >= exposure_round
                    for action_round in reaction_index.get((user_id, post_key), [])
                )
                reply_match = any(
                    action_round >= exposure_round
                    for action_round in reply_index.get((user_id, post_key), [])
                )
                mention_match = any(
                    action_round >= exposure_round
                    for action_round in mention_index.get((user_id, str(author_id)), [])
                )

                if reaction_match:
                    conversion_counts["reaction"] += 1
                if reply_match:
                    conversion_counts["reply"] += 1
                if mention_match:
                    conversion_counts["mention"] += 1
                if reaction_match or reply_match or mention_match:
                    conversion_counts["any"] += 1

                timeline_rows.append(
                    {
                        "round": exposure_round,
                        "exposure_count": 1,
                        "reaction_conversions": int(reaction_match),
                        "reply_conversions": int(reply_match),
                        "mention_conversions": int(mention_match),
                        "any_conversion": int(
                            reaction_match or reply_match or mention_match
                        ),
                    }
                )

        timeline = (
            pd.DataFrame(timeline_rows)
            .groupby("round", as_index=False)
            .sum(numeric_only=True)
            if timeline_rows
            else pd.DataFrame(
                columns=[
                    "round",
                    "exposure_count",
                    "reaction_conversions",
                    "reply_conversions",
                    "mention_conversions",
                    "any_conversion",
                ]
            )
        )

        exposure_count = int(sum(exposure_by_post.values()))
        unique_posts = int(len(exposure_by_post))
        unique_recipients = int(len(exposure_by_recipient))
        unique_authors = int(len({author for author in post_author_by_key.values()}))
        repeat_pair_exposures = int(
            sum(max(count - 1, 0) for count in exposure_by_pair.values())
        )
        post_counts = list(exposure_by_post.values())
        total_exposures = float(exposure_count)
        top_post_share = (
            max(post_counts) / total_exposures if post_counts and total_exposures else 0.0
        )
        if post_counts:
            top_n = max(1, int(len(post_counts) * 0.1))
            top_decile_share = (
                sum(sorted(post_counts, reverse=True)[:top_n]) / total_exposures
                if total_exposures
                else 0.0
            )
            exposure_concentration = sum(
                (count / total_exposures) ** 2 for count in post_counts
            )
        else:
            top_decile_share = 0.0
            exposure_concentration = 0.0

        conversion_rates = {
            key: (value / exposure_count) if exposure_count else 0.0
            for key, value in conversion_counts.items()
        }
        for key in ("reaction", "reply", "mention", "any"):
            conversion_counts.setdefault(key, 0)
            conversion_rates.setdefault(key, 0.0)

        result = {
            "available": True,
            "exposure_count": exposure_count,
            "unique_recipients": unique_recipients,
            "unique_posts": unique_posts,
            "unique_authors": unique_authors,
            "exposure_by_post": dict(exposure_by_post),
            "exposure_by_recipient": dict(exposure_by_recipient),
            "conversion_counts": {
                key: int(conversion_counts.get(key, 0))
                for key in ("reaction", "reply", "mention", "any")
            },
            "conversion_rates": conversion_rates,
            "feedback_loop": {
                "repeat_pair_exposures": repeat_pair_exposures,
                "repeat_pair_rate": (
                    repeat_pair_exposures / exposure_count if exposure_count else 0.0
                ),
                "top_post_share": top_post_share,
                "top_decile_share": top_decile_share,
                "exposure_concentration": exposure_concentration,
            },
            "timeline": timeline.sort_values("round").reset_index(drop=True),
        }
        return self.__analysis_cache_set(
            result,
            "recommendation_exposure_summary",
            from_round=from_round,
            to_round=to_round,
        )

    recommendation_feedback_summary = recommendation_exposure_summary

    # Agent profiles
    @_handle_db_connection
    def agent_reactions(self, agent_id, from_round=None, to_round=None):
        """
        Get all reactions made by a specific agent.

        Returns reactions (likes, loves, etc.) that an agent has given to posts,
        optionally filtered by time range. Results are grouped by reaction type.

        :param agent_id: The ID of the agent
        :type agent_id: Any
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping reaction types to lists of post identifiers
        :rtype: dict[str, list]

        Example::

            ydh = YDataHandler('path/to/database.db')

            reactions = ydh.agent_reactions(agent_id=<agent_identifier>)
            print("Selected agent's reactions:")
            for reaction_type, post_ids in reactions.items():
                print(f"  {reaction_type}: {len(post_ids)} posts")

            # Reactions in specific time range
            reactions = ydh.agent_reactions(agent_id=<agent_identifier>, from_round=100, to_round=200)
            like_count = len(reactions.get('like', []))
            print(f"Likes in rounds 100-200: {like_count}")

        See Also:
            :meth:`agent_hashtags`: Get hashtags used by agent
            :meth:`agent_interests`: Get interests of agent
        """
        time_filter, time_params = self.__build_time_filter(from_round, to_round)
        query = f"SELECT post_id, type FROM reactions WHERE user_id = ?{time_filter}"
        data = self.__execute_query(query, (agent_id, *time_params))

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
        :type agent_id: Any
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping hashtags to their usage counts
        :rtype: dict[str, int]

        Example::

            ydh = YDataHandler('path/to/database.db')

            hashtags = ydh.agent_hashtags(agent_id=<agent_identifier>)
            print("Selected agent's most used hashtags:")
            for tag, count in sorted(hashtags.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  #{tag}: {count} times")

            # Hashtags in specific period
            recent_tags = ydh.agent_hashtags(agent_id=<agent_identifier>, from_round=500, to_round=1000)
            print(f"Used {len(recent_tags)} different hashtags in rounds 500-1000")

        See Also:
            :meth:`agent_interests`: Get interests of agent
            :meth:`agent_topics`: Get topics agent engages with
        """
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            "SELECT h.hashtag FROM post_hashtags as ph, post as p, hashtags as h "
            "WHERE p.user_id = ? AND p.id = ph.post_id AND ph.hashtag_id = h.id"
            f"{time_filter}"
        )
        data = self.__execute_query(query, (agent_id, *time_params))

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
        :type agent_id: Any
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping interests to their frequency counts
        :rtype: dict[str, int]

        Example::

            ydh = YDataHandler('path/to/database.db')

            interests = ydh.agent_interests(agent_id=<agent_identifier>)
            print("Selected agent's interest profile:")
            for interest, count in sorted(interests.items(), key=lambda x: x[1], reverse=True):
                print(f"  {interest}: {count}")

            # Track interest evolution
            early_interests = ydh.agent_interests(agent_id=<agent_identifier>, from_round=0, to_round=500)
            late_interests = ydh.agent_interests(agent_id=<agent_identifier>, from_round=500, to_round=1000)

            new_interests = set(late_interests.keys()) - set(early_interests.keys())
            print(f"New interests acquired: {new_interests}")

        See Also:
            :meth:`agent_hashtags`: Get hashtags used by agent
            :meth:`agent_emotions`: Get emotional profile of agent
        """

        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "ui.round_id"
        )
        query = (
            "SELECT i.interest FROM user_interest as ui, interests as i "
            "WHERE user_id = ? AND i.iid = ui.interest_id"
            f"{time_filter}"
        )
        data = self.__execute_query(query, (agent_id, *time_params))

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
        :type agent_id: Any
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: Dictionary mapping emotions to their frequency counts
        :rtype: dict[str, int]

        Example::

            ydh = YDataHandler('path/to/database.db')

            emotions = ydh.agent_emotions(agent_id=<agent_identifier>)
            print("Selected agent's emotional expression:")
            for emotion, count in sorted(emotions.items(), key=lambda x: x[1], reverse=True):
                print(f"  {emotion}: {count} posts")

            # Compare emotional states over time
            early_emotions = ydh.agent_emotions(agent_id=<agent_identifier>, from_round=0, to_round=500)
            late_emotions = ydh.agent_emotions(agent_id=<agent_identifier>, from_round=500, to_round=1000)

            joy_change = late_emotions.get('joy', 0) - early_emotions.get('joy', 0)
            print(f"Change in joy expression: {joy_change}")

        See Also:
            :meth:`agent_toxicity`: Get toxicity profile
            :meth:`agent_interests`: Get interest profile
        """
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            "SELECT e.emotion FROM post as p, post_emotions as pe, emotions as e "
            "WHERE p.user_id = ? AND p.id = pe.post_id AND e.id = pe.emotion_id"
            f"{time_filter}"
        )
        data = self.__execute_query(query, (agent_id, *time_params))

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
        :type agent_id: Any
        :param from_round: Starting round for filtering (inclusive), None for no lower bound
        :type from_round: int, optional
        :param to_round: Ending round for filtering (inclusive), None for no upper bound
        :type to_round: int, optional
        :return: List of dictionaries, each containing toxicity scores for a post
        :rtype: list[dict]

        Example::

            ydh = YDataHandler('path/to/database.db')

            toxicity_data = ydh.agent_toxicity(agent_id=<agent_identifier>)
            print(f"Selected agent toxicity analysis over {len(toxicity_data)} posts:")

            # Calculate average toxicity
            if toxicity_data:
                avg_tox = sum(p['toxicity'] for p in toxicity_data) / len(toxicity_data)
                print(f"Average toxicity: {avg_tox:.3f}")

                # Check for specific toxic behaviors
                high_profanity = [p for p in toxicity_data if p['profanity'] > 0.7]
                print(f"Posts with high profanity: {len(high_profanity)}")

            # Compare toxicity over time periods
            early_tox = ydh.agent_toxicity(agent_id=<agent_identifier>, from_round=0, to_round=500)
            late_tox = ydh.agent_toxicity(agent_id=<agent_identifier>, from_round=500, to_round=1000)

        Note:
            Toxicity scores are typically in the range [0, 1] where higher values
            indicate more toxic content.

        See Also:
            :meth:`agent_emotions`: Get emotional profile
            :meth:`posts_by_agent`: Get full post objects with toxicity data
        """
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            "SELECT "
            "pt.toxicity, "
            "pt.severe_toxicity, "
            "pt.identity_attack, "
            "pt.insult, "
            "pt.profanity, "
            "pt.threat, "
            "pt.sexually_explicit, "
            "pt.flirtation "
            "FROM post as p, post_toxicity as pt "
            "WHERE p.user_id = ? AND p.id = pt.post_id"
            f"{time_filter} "
            "ORDER BY p.round ASC"
        )
        data = self.__execute_query(query, (agent_id, *time_params))

        toxicity = []
        for row in data:
            toxicity.append(
                {
                    "toxicity": row[0],
                    "severe_toxicity": row[1],
                    "identity_attack": row[2],
                    "insult": row[3],
                    "profanity": row[4],
                    "threat": row[5],
                    "sexual_explicit": row[6],
                    "flirtation": row[7],
                }
            )

        return toxicity

    def __agent_posts_rows(self, agent_id, from_round=None, to_round=None):
        """
        Load raw post rows for an agent, optionally filtered by round.
        """
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "round"
        )
        query = f"SELECT * FROM post WHERE user_id = ?{time_filter} ORDER BY round ASC, id ASC"
        return self.__execute_query(query, (agent_id, *time_params))

    @_handle_db_connection
    def user_profile_summary(self, agent_id, from_round=None, to_round=None):
        """
        Build a compact profile for a user from their content and interaction traces.
        """
        cached = self.__analysis_cache_get(
            "user_profile_summary",
            agent_id,
            from_round=from_round,
            to_round=to_round,
        )
        if cached is not None:
            return cached

        schema = self.__get_schema()
        post_rows = self.__agent_posts_rows(
            agent_id, from_round=from_round, to_round=to_round
        )

        dimensions = []
        for feature_name, dimension in (
            ("topics", "topics"),
            ("emotions", "emotions"),
            ("toxicity", "toxicity"),
            ("mentions", "mentions"),
            ("hashtags", "hashtags"),
        ):
            if schema.supports_feature(feature_name):
                dimensions.append(dimension)

        posts = Posts()
        cursor = self.__get_cursor()
        for row in post_rows:
            post = Post(row)
            if dimensions:
                post.enrich_post(cursor, dimensions)
            posts.add_post(post)

        post_list = posts.get_posts()
        post_count = len(post_list)
        reply_count = sum(1 for post in post_list if post.comment_to not in (None, -1))
        original_post_count = post_count - reply_count
        reply_ratio = (reply_count / post_count) if post_count else 0.0

        topic_counts = defaultdict(int)
        emotion_counts = defaultdict(int)
        hashtag_counts = defaultdict(int)
        toxicity_scores = defaultdict(list)
        semantic_profiles = []

        for post in post_list:
            semantic_profiles.append(self.__text_profile(post.text))
            for topic in post.topics:
                topic_counts[topic] += 1
            for emotion in post.emotions:
                emotion_counts[emotion] += 1
            for hashtag in post.hashtags:
                hashtag_counts[hashtag] += 1
            if post.toxicity:
                for key, value in post.toxicity.items():
                    toxicity_scores[key].append(value)

        avg_toxicity = (
            sum(toxicity_scores["toxicity"]) / len(toxicity_scores["toxicity"])
            if toxicity_scores["toxicity"]
            else 0.0
        )
        toxicity_max = (
            max(toxicity_scores["toxicity"]) if toxicity_scores["toxicity"] else 0.0
        )

        if semantic_profiles:
            semantic_profile = {}
            for key in semantic_profiles[0].keys():
                semantic_profile[key] = sum(
                    profile[key] for profile in semantic_profiles
                ) / len(semantic_profiles)
        else:
            semantic_profile = {
                "character_count": 0.0,
                "token_count": 0.0,
                "word_count": 0.0,
                "unique_word_count": 0.0,
                "type_token_ratio": 0.0,
                "avg_word_length": 0.0,
                "url_count": 0.0,
                "hashtag_count": 0.0,
                "mention_count": 0.0,
                "punctuation_count": 0.0,
                "punctuation_ratio": 0.0,
                "uppercase_ratio": 0.0,
                "digit_count": 0.0,
                "entropy_proxy": 0.0,
            }

        if post_count == 0:
            segment = "lurker"
        elif avg_toxicity >= 0.5:
            segment = "polarized"
        elif reply_ratio >= 0.5:
            segment = "conversationalist"
        elif len(topic_counts) >= 3:
            segment = "multitopic"
        elif post_count >= 5:
            segment = "active_poster"
        else:
            segment = "observer"

        result = {
            "agent_id": agent_id,
            "from_round": from_round,
            "to_round": to_round,
            "post_count": post_count,
            "reply_count": reply_count,
            "original_post_count": original_post_count,
            "reply_ratio": reply_ratio,
            "topic_counts": dict(topic_counts),
            "emotion_counts": dict(emotion_counts),
            "hashtag_counts": dict(hashtag_counts),
            "avg_toxicity": avg_toxicity,
            "max_toxicity": toxicity_max,
            "semantic_profile": semantic_profile,
            "segment": segment,
        }
        return self.__analysis_cache_set(
            result,
            "user_profile_summary",
            agent_id,
            from_round=from_round,
            to_round=to_round,
        )

    @_handle_db_connection
    def profile_drift(self, agent_id, split_round=None):
        """
        Compare a user's early and late profiles across a round boundary.
        """
        cached = self.__analysis_cache_get(
            "profile_drift", agent_id, split_round=split_round
        )
        if cached is not None:
            return cached

        rows = self.__agent_posts_rows(agent_id)
        if not rows:
            result = {
                "agent_id": agent_id,
                "split_round": split_round,
                "early": self.user_profile_summary(agent_id, to_round=split_round),
                "late": self.user_profile_summary(agent_id, from_round=split_round),
                "topic_jaccard": 0.0,
                "emotion_jaccard": 0.0,
                "toxicity_delta": 0.0,
                "reply_ratio_delta": 0.0,
                "post_count_delta": 0,
                "segment_shift": None,
            }
            return self.__analysis_cache_set(
                result,
                "profile_drift",
                agent_id,
                split_round=split_round,
            )

        if split_round is None:
            midpoint = len(rows) // 2
            split_round = rows[midpoint][6]

        early = self.user_profile_summary(agent_id, to_round=split_round)
        late_from_round = (
            split_round + 1 if isinstance(split_round, int) else split_round
        )
        late = self.user_profile_summary(agent_id, from_round=late_from_round)

        def _jaccard(left, right):
            left_keys = set(left.keys())
            right_keys = set(right.keys())
            union = left_keys | right_keys
            if not union:
                return 0.0
            return len(left_keys & right_keys) / len(union)

        result = {
            "agent_id": agent_id,
            "split_round": split_round,
            "early": early,
            "late": late,
            "topic_jaccard": _jaccard(early["topic_counts"], late["topic_counts"]),
            "emotion_jaccard": _jaccard(
                early["emotion_counts"], late["emotion_counts"]
            ),
            "toxicity_delta": late["avg_toxicity"] - early["avg_toxicity"],
            "reply_ratio_delta": late["reply_ratio"] - early["reply_ratio"],
            "post_count_delta": late["post_count"] - early["post_count"],
            "segment_shift": f"{early['segment']}->{late['segment']}",
        }
        return self.__analysis_cache_set(
            result,
            "profile_drift",
            agent_id,
            split_round=split_round,
        )

    @_handle_db_connection
    def user_segments(self, from_round=None, to_round=None, graph=None):
        """
        Segment users into coarse behavioral groups.
        """
        if self.__get_schema().has_table("user_mgmt"):
            users = self.users_frame(columns=["id"])
            user_ids = list(users["id"].tolist())
        else:
            user_ids = []

        rows = []
        for user_id in user_ids:
            summary = self.user_profile_summary(
                user_id, from_round=from_round, to_round=to_round
            )
            rows.append(
                {
                    "agent_id": user_id,
                    "segment": summary["segment"],
                    "post_count": summary["post_count"],
                    "reply_ratio": summary["reply_ratio"],
                    "topic_diversity": len(summary["topic_counts"]),
                    "emotion_diversity": len(summary["emotion_counts"]),
                    "avg_toxicity": summary["avg_toxicity"],
                }
            )

        import pandas as pd

        return pd.DataFrame(rows)

    @_handle_db_connection
    def community_metrics(
        self, graph=None, graph_type="social", from_round=None, to_round=None
    ):
        """
        Measure community structure and polarization in an interaction graph.
        """
        if graph is None:
            if graph_type == "mention":
                graph = self.mention_network(from_round=from_round, to_round=to_round)
            elif graph_type == "social":
                graph = self.social_network(from_round=from_round, to_round=to_round)
            else:
                raise ValueError(
                    "graph_type must be 'social' or 'mention' when graph is not provided."
                )

        if graph.number_of_nodes() == 0:
            return {
                "graph_type": graph_type,
                "node_count": 0,
                "edge_count": 0,
                "community_count": 0,
                "communities": [],
                "community_sizes": [],
                "modularity": 0.0,
                "cross_community_edge_ratio": 0.0,
                "density": 0.0,
                "reciprocity": 0.0,
                "leaning_alignment_ratio": None,
            }

        undirected = graph.to_undirected()
        if undirected.number_of_edges() > 0 and undirected.number_of_nodes() > 1:
            communities = list(
                nx.algorithms.community.greedy_modularity_communities(undirected)
            )
            modularity = (
                nx.algorithms.community.modularity(undirected, communities)
                if len(communities) > 1
                else 0.0
            )
        else:
            communities = [set(undirected.nodes())]
            modularity = 0.0

        community_map = {}
        for index, community in enumerate(communities):
            for node in community:
                community_map[node] = index

        cross_edges = 0
        for source, target in graph.edges():
            if community_map.get(source) != community_map.get(target):
                cross_edges += 1
        total_edges = graph.number_of_edges()
        cross_ratio = (cross_edges / total_edges) if total_edges else 0.0

        leaning_alignment_ratio = None
        if (
            self.__get_schema().has_column("user_mgmt", "leaning")
            and graph.number_of_edges() > 0
        ):
            user_frame = self.users_frame(columns=["id", "leaning"])
            leaning_by_user = {row[0]: row[1] for _, row in user_frame.iterrows()}
            aligned = 0
            comparable = 0
            for source, target in graph.edges():
                source_leaning = leaning_by_user.get(source)
                target_leaning = leaning_by_user.get(target)
                if source_leaning is None or target_leaning is None:
                    continue
                comparable += 1
                if source_leaning == target_leaning:
                    aligned += 1
            if comparable:
                leaning_alignment_ratio = aligned / comparable

        reciprocity = nx.reciprocity(graph) if graph.number_of_edges() else 0.0

        return {
            "graph_type": graph_type,
            "node_count": graph.number_of_nodes(),
            "edge_count": total_edges,
            "community_count": len(communities),
            "communities": [sorted(list(community)) for community in communities],
            "community_sizes": [len(community) for community in communities],
            "largest_community_size": max(
                (len(community) for community in communities), default=0
            ),
            "modularity": modularity,
            "cross_community_edge_ratio": cross_ratio,
            "density": (
                nx.density(undirected) if undirected.number_of_nodes() > 1 else 0.0
            ),
            "reciprocity": reciprocity if reciprocity is not None else 0.0,
            "leaning_alignment_ratio": leaning_alignment_ratio,
        }

    def __forum_messages_table(self):
        """
        Resolve the active forum messages table name.
        """
        schema = self.__get_schema()
        return schema.resolve_table("forum_messages")

    def __forum_message_text_column(self, table_name=None):
        """
        Resolve the active forum message text column name.
        """
        schema = self.__get_schema()
        table_name = table_name or self.__forum_messages_table()
        for column_name in ("content", "message", "text"):
            if schema.has_column(table_name, column_name):
                return column_name
        raise ValueError("Forum message text column was not found in this dataset.")

    def __reported_posts_frame(self, from_round=None, to_round=None):
        """
        Build a dataframe of reported content events.
        """
        import pandas as pd

        schema = self.__get_schema()
        if not schema.has_table("reported"):
            return pd.DataFrame()

        time_filter = ""
        params = []
        if schema.has_table("post"):
            time_filter, params = self.__build_time_filter(
                from_round, to_round, "p.round"
            )

        query = (
            "SELECT r.id AS report_id, r.type AS report_type, r.to_uid AS reported_user_id, "
            "r.to_post AS reported_post_id, r.from_uid AS reporter_user_id, r.tid AS thread_id"
        )
        if schema.has_table("post"):
            query += ", p.round AS post_round, p.thread_id AS post_thread_id"
        query += " FROM reported AS r"
        if schema.has_table("post"):
            query += " LEFT JOIN post AS p ON p.id = r.to_post"
            query += f" WHERE 1=1{time_filter}"
        query += " ORDER BY r.id ASC"
        rows = self.__execute_query(query, tuple(params))
        columns = [
            "report_id",
            "report_type",
            "reported_user_id",
            "reported_post_id",
            "reporter_user_id",
            "thread_id",
        ]
        if schema.has_table("post"):
            columns.extend(["post_round", "post_thread_id"])
        return pd.DataFrame(rows, columns=columns)

    @_handle_db_connection
    def moderation_summary(self, from_round=None, to_round=None):
        """
        Summarize reported-content and moderation signals.
        """
        cached = self.__analysis_cache_get(
            "moderation_summary",
            from_round=from_round,
            to_round=to_round,
        )
        if cached is not None:
            return cached

        schema = self.__get_schema()
        reports = self.__reported_posts_frame(from_round=from_round, to_round=to_round)
        report_types = {}
        if not reports.empty:
            report_types = reports["report_type"].value_counts().to_dict()

        moderated_posts = 0
        moderated_comments = 0
        if schema.has_table("post") and schema.has_column("post", "moderated"):
            time_filter, params = self.__build_time_filter(
                from_round, to_round, "p.round"
            )
            query = (
                "SELECT "
                "COUNT(*) AS moderated_posts, "
                "SUM(CASE WHEN p.is_moderation_comment IS NOT NULL AND p.is_moderation_comment != 0 THEN 1 ELSE 0 END) AS moderation_comments "
                "FROM post AS p "
                f"WHERE p.moderated IS NOT NULL AND p.moderated != 0{time_filter}"
            )
            rows = self.__execute_query(query, params)
            if rows:
                moderated_posts = int(rows[0][0] or 0)
                moderated_comments = int(rows[0][1] or 0)

        summary = {
            "report_count": int(len(reports)),
            "unique_reported_posts": (
                int(reports["reported_post_id"].nunique()) if not reports.empty else 0
            ),
            "unique_reported_users": (
                int(reports["reported_user_id"].nunique()) if not reports.empty else 0
            ),
            "unique_reporters": (
                int(reports["reporter_user_id"].nunique()) if not reports.empty else 0
            ),
            "report_types": report_types,
            "moderated_posts": moderated_posts,
            "moderation_comments": moderated_comments,
        }
        if schema.has_table("sys_messages"):
            summary["sys_message_count"] = len(self.table_frame("sys_messages"))
        else:
            summary["sys_message_count"] = 0
        return self.__analysis_cache_set(
            summary,
            "moderation_summary",
            from_round=from_round,
            to_round=to_round,
        )

    @_handle_db_connection
    def moderation_hotspots(self, top_n=10, from_round=None, to_round=None):
        """
        Rank the most frequently reported users and posts.
        """
        import pandas as pd

        reports = self.__reported_posts_frame(from_round=from_round, to_round=to_round)
        if reports.empty:
            return pd.DataFrame(columns=["entity_type", "entity_id", "report_count"])

        post_counts = (
            reports.groupby("reported_post_id")
            .size()
            .reset_index(name="report_count")
            .rename(columns={"reported_post_id": "entity_id"})
        )
        post_counts.insert(0, "entity_type", "post")

        user_counts = (
            reports.groupby("reported_user_id")
            .size()
            .reset_index(name="report_count")
            .rename(columns={"reported_user_id": "entity_id"})
        )
        user_counts.insert(0, "entity_type", "user")

        combined = pd.concat([post_counts, user_counts], ignore_index=True)
        combined = combined.sort_values(
            ["report_count", "entity_type", "entity_id"], ascending=[False, True, True]
        )
        return combined.head(top_n).reset_index(drop=True)

    def __forum_session_message_frame(self, session_id):
        """
        Load the messages for a forum session as a dataframe.
        """
        import pandas as pd

        table_name = self.__forum_messages_table()
        text_column = self.__forum_message_text_column(table_name)
        schema = self.__get_schema()
        columns = ["id", "session_id", text_column]
        optional_columns = []
        for column_name in (
            "role",
            "meta_json",
            "created_at",
            "round",
            "user_id",
            "reply_to",
        ):
            if schema.has_column(table_name, column_name):
                optional_columns.append(column_name)
        query = f"SELECT {', '.join(columns + optional_columns)} FROM {table_name} WHERE session_id = ? ORDER BY id ASC"
        rows = self.__execute_query(query, (session_id,))
        return pd.DataFrame(
            rows, columns=["id", "session_id", text_column, *optional_columns]
        )

    @_handle_db_connection
    def forum_session_summary(self, session_id):
        """
        Summarize a forum conversation session.
        """
        cached = self.__analysis_cache_get("forum_session_summary", session_id)
        if cached is not None:
            return cached

        sessions_table = self.__get_schema().resolve_table("forum_sessions")
        session_rows, session_columns = self.__execute_query_with_columns(
            f"SELECT * FROM {sessions_table} WHERE id = ?", (session_id,)
        )
        if not session_rows:
            raise ValueError(
                f"Forum session ID {session_id} does not exist in the database."
            )

        session_row = dict(zip(session_columns, session_rows[0]))
        messages = self.__forum_session_message_frame(session_id)
        if messages.empty:
            result = {
                "session_id": session_id,
                "message_count": 0,
                "participant_count": 0,
                "reply_count": 0,
                "turn_balance": 0.0,
                "session_span": None,
                "owner_user_id": session_row.get("owner_user_id"),
                "target_user_id": session_row.get("target_user_id"),
                "last_message_preview": session_row.get("last_message_preview"),
            }
            return self.__analysis_cache_set(
                result,
                "forum_session_summary",
                session_id,
            )

        schema = self.__get_schema()
        participant_count = 0
        if "user_id" in messages.columns:
            participant_count = int(messages["user_id"].nunique())
        elif "role" in messages.columns:
            participant_count = int(messages["role"].nunique())
        elif schema.has_column(sessions_table, "owner_user_id") and schema.has_column(
            sessions_table, "target_user_id"
        ):
            participant_count = len(
                {
                    session_row.get("owner_user_id"),
                    session_row.get("target_user_id"),
                }
                - {None, ""}
            )

        reply_count = 0
        if "reply_to" in messages.columns:
            reply_count = int(messages["reply_to"].notna().sum())
        elif "role" in messages.columns:
            reply_count = max(int(len(messages) - 1), 0)

        if "round" in messages.columns and not messages["round"].isna().all():
            session_span = int(messages["round"].max() - messages["round"].min())
        elif "created_at" in messages.columns:
            session_span = (
                f"{messages['created_at'].min()}..{messages['created_at'].max()}"
            )
        else:
            session_span = None

        if "role" in messages.columns:
            role_counts = messages["role"].value_counts().to_dict()
            turn_balance = 0.0
            if len(role_counts) > 1:
                counts = list(role_counts.values())
                turn_balance = min(counts) / max(counts)
        else:
            role_counts = {}
            turn_balance = 1.0 if len(messages) <= 1 else 0.5

        result = {
            "session_id": session_id,
            "message_count": int(len(messages)),
            "participant_count": participant_count,
            "reply_count": reply_count,
            "turn_balance": turn_balance,
            "session_span": session_span,
            "role_counts": role_counts,
            "owner_user_id": session_row.get("owner_user_id"),
            "target_user_id": session_row.get("target_user_id"),
            "last_message_preview": session_row.get("last_message_preview"),
        }
        return self.__analysis_cache_set(result, "forum_session_summary", session_id)

    @_handle_db_connection
    def forum_session_summaries(self):
        """
        Summarize every forum session in the dataset.
        """
        cached = self.__analysis_cache_get("forum_session_summaries")
        if cached is not None:
            return cached

        sessions_table = self.__get_schema().resolve_table("forum_sessions")
        sessions = self.__execute_query(
            f"SELECT id FROM {sessions_table} ORDER BY id ASC"
        )
        summaries = {}
        for row in sessions:
            session_id = row[0]
            summaries[session_id] = self.forum_session_summary(session_id)
        return self.__analysis_cache_set(summaries, "forum_session_summaries")

    @_handle_db_connection
    def summary_report(self):
        """
        Produce a high-level report for the current experiment.
        """
        cached = self.__analysis_cache_get("summary_report")
        if cached is not None:
            return cached

        schema = self.__get_schema()
        report = {
            "db_path": self.db_path,
            "db_type": self.db_type,
            "capabilities": schema.describe()["features"],
            "table_count": len(schema.tables),
        }

        if schema.has_table("user_mgmt"):
            users_table = schema.resolve_table("users")
            report["user_count"] = int(
                self.__execute_query(f"SELECT COUNT(*) FROM {users_table}")[0][0]
            )
        else:
            report["user_count"] = 0

        if schema.has_table("post"):
            post_rows, post_columns = self.__execute_query_with_columns(
                "SELECT * FROM post"
            )
            post_index = {
                column_name: idx for idx, column_name in enumerate(post_columns)
            }
            report["post_count"] = len(post_rows)
            if "comment_to" in post_index:
                report["reply_count"] = int(
                    sum(
                        1
                        for row in post_rows
                        if row[post_index["comment_to"]] not in (None, -1)
                    )
                )
            else:
                report["reply_count"] = 0
            thread_rows = self.__execute_query(
                "SELECT DISTINCT CASE WHEN thread_id IS NULL OR thread_id = -1 THEN id ELSE thread_id END FROM post"
            )
            report["thread_count"] = len(thread_rows)
        else:
            report["post_count"] = 0
            report["reply_count"] = 0
            report["thread_count"] = 0

        if schema.supports_feature("topics"):
            topic_rows = self.__execute_query(
                "SELECT COUNT(DISTINCT topic_id) FROM post_topics"
            )
            report["topic_count"] = int(topic_rows[0][0]) if topic_rows else 0
        else:
            report["topic_count"] = 0

        report["report_count"] = (
            len(self.__reported_posts_frame()) if schema.has_table("reported") else 0
        )
        try:
            sessions_table = schema.resolve_table("forum_sessions")
            report["forum_session_count"] = int(
                self.__execute_query(f"SELECT COUNT(*) FROM {sessions_table}")[0][0]
            )
        except KeyError:
            report["forum_session_count"] = 0

        try:
            messages_table = schema.resolve_table("forum_messages")
            report["forum_message_count"] = int(
                self.__execute_query(f"SELECT COUNT(*) FROM {messages_table}")[0][0]
            )
        except KeyError:
            report["forum_message_count"] = 0
        report["social_edge_count"] = (
            int(self.__execute_query("SELECT COUNT(*) FROM follow")[0][0])
            if schema.has_table("follow")
            else 0
        )
        report["mention_edge_count"] = (
            int(self.__execute_query("SELECT COUNT(*) FROM mentions")[0][0])
            if schema.has_table("mentions")
            else 0
        )
        return self.__analysis_cache_set(report, "summary_report")

    @_handle_db_connection
    def summary_frame(self):
        """
        Return the summary report as a one-row dataframe.
        """
        import pandas as pd

        cached = self.__analysis_cache_get("summary_frame")
        if cached is not None:
            return cached

        frame = pd.DataFrame([self.summary_report()])
        return self.__analysis_cache_set(frame, "summary_frame")

    @_handle_db_connection
    def recommended_indexes(self):
        """
        Return a practical set of index recommendations for common analytics paths.
        """
        schema = self.__get_schema()
        suggestions = []

        def add(table_name, index_name, columns):
            if schema.has_table(table_name):
                resolved_table = schema.resolve_table(table_name)
                suggestions.append(
                    {
                        "table": resolved_table,
                        "index_name": index_name,
                        "columns": columns,
                        "sql": f"CREATE INDEX IF NOT EXISTS {index_name} ON {resolved_table} ({', '.join(columns)});",
                    }
                )

        add("post", "idx_post_user_round", ["user_id", "round"])
        add("post", "idx_post_thread_round", ["thread_id", "round"])
        add("post", "idx_post_comment_to", ["comment_to"])
        add("post", "idx_post_round", ["round"])
        add("reactions", "idx_reactions_user_round", ["user_id", "round"])
        add("reactions", "idx_reactions_post", ["post_id"])
        add("recommendations", "idx_recommendations_user_round", ["user_id", "round"])
        add("mentions", "idx_mentions_user_round", ["user_id", "round"])
        add("mentions", "idx_mentions_post", ["post_id"])
        add("post_topics", "idx_post_topics_topic_post", ["topic_id", "post_id"])
        add("post_hashtags", "idx_post_hashtags_post", ["post_id", "hashtag_id"])
        add("user_interest", "idx_user_interest_user_round", ["user_id", "round_id"])
        add("user_interest", "idx_user_interest_interest", ["interest_id"])
        add("follow", "idx_follow_user_round", ["user_id", "round"])
        add("follow", "idx_follow_follower_round", ["follower_id", "round"])
        add("forum_chat_messages", "idx_forum_messages_session", ["session_id", "id"])
        add("reported", "idx_reported_post", ["to_post"])
        add("reported", "idx_reported_user", ["to_uid"])
        add("reported", "idx_reported_thread", ["tid"])
        add("post_toxicity", "idx_post_toxicity_post", ["post_id"])
        add("post_sentiment", "idx_post_sentiment_post", ["post_id"])
        add("post_emotions", "idx_post_emotions_post", ["post_id"])

        return {
            "suggestions": suggestions,
            "count": len(suggestions),
        }

    @_handle_db_connection
    def benchmark_analytics(self, iterations=3):
        """
        Measure a small set of analytics paths and cache their outputs.
        """
        import time

        metrics = {}
        targets = []

        if self.__get_schema().has_table("post"):
            targets.append(("summary_report", self.summary_report))
            targets.append(("summary_frame", self.summary_frame))

        if self.__get_schema().has_table("reported"):
            targets.append(("moderation_summary", self.moderation_summary))

        if self.__get_schema().has_table("forum_chat_sessions"):
            targets.append(("forum_session_summaries", self.forum_session_summaries))

        if self.__get_schema().supports_feature("topics"):
            topic_rows = self.__execute_query(
                "SELECT DISTINCT topic_id FROM post_topics ORDER BY topic_id ASC"
            )
            if topic_rows:
                first_topic = topic_rows[0][0]
                targets.append(
                    (
                        f"topic_lifecycle[{first_topic}]",
                        lambda: self.topic_lifecycle(first_topic),
                    )
                )

        if self.__get_schema().has_table("user_mgmt"):
            targets.append(("user_segments", self.user_segments))

        for name, func in targets:
            self._analysis_cache.clear()
            warm = func()
            warm_times = []
            for _ in range(max(iterations, 1)):
                start = time.perf_counter()
                func()
                warm_times.append(time.perf_counter() - start)
            metrics[name] = {
                "cached": name in self.__analysis_cache_info()["keys"],
                "warmup_type": type(warm).__name__,
                "iterations": max(iterations, 1),
                "average_seconds": sum(warm_times) / len(warm_times),
                "min_seconds": min(warm_times),
                "max_seconds": max(warm_times),
            }

        return {
            "iterations": max(iterations, 1),
            "metrics": metrics,
        }

    @_handle_db_connection
    def export_summary_csv(self, path):
        """
        Export the experiment summary report to CSV.
        """
        self.summary_frame().to_csv(path, index=False)
        return path

    @_handle_db_connection
    def export_summary_json(self, path):
        """
        Export the experiment summary report to JSON.
        """
        import json

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                self.summary_report(), handle, indent=2, sort_keys=True, default=str
            )
        return path

    @_handle_db_connection
    def compare_experiments(self, other, metrics=None):
        """
        Compare this experiment with another dataset or handler.
        """
        if isinstance(other, YDataHandler):
            other_handler = other
        else:
            other_handler = YDataHandler(other)

        left = self.summary_report()
        right = other_handler.summary_report()
        if metrics is None:
            metrics = sorted(set(left.keys()) & set(right.keys()))

        comparison = {}
        for metric in metrics:
            left_value = left.get(metric)
            right_value = right.get(metric)
            if isinstance(left_value, (int, float)) and isinstance(
                right_value, (int, float)
            ):
                delta = right_value - left_value
                comparison[metric] = {
                    "left": left_value,
                    "right": right_value,
                    "delta": delta,
                    "relative_change": (delta / left_value) if left_value else None,
                }
            else:
                comparison[metric] = {
                    "left": left_value,
                    "right": right_value,
                    "equal": left_value == right_value,
                }

        return {
            "left": left,
            "right": right,
            "metrics": comparison,
        }

    # Network Extraction Methods #
    @_handle_db_connection
    def ego_network_follower(self, agent_id, from_round=None, to_round=None):
        """
        Extract the follower ego network for a specific agent.

        Returns a directed network showing agents who follow the specified agent.
        The network accounts for follow/unfollow dynamics, keeping only active
        connections at the end of the time period.

        :param agent_id: The ID of the agent (the "ego")
        :type agent_id: Any
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
            agent_id = next(iter(ydh.agent_mapping()))

            # Get follower network for a selected agent
            follower_net = ydh.ego_network_follower(agent_id=agent_id)
            print(f"Selected agent has {follower_net.number_of_nodes() - 1} followers")
            print(f"Follower IDs: {list(follower_net.successors(agent_id))}")

            # Get follower network in specific time period
            recent_followers = ydh.ego_network_follower(agent_id=agent_id, from_round=500, to_round=1000)

        Note:
            This method tracks follow/unfollow actions. If an edge has been
            followed and then unfollowed (even number of actions), it is removed
            from the final network.

        See Also:
            :meth:`ego_network_following`: Get accounts the agent follows
            :meth:`ego_network`: Get complete ego network (both followers and following)
        """
        time_filter, time_params = self.__build_time_filter(from_round, to_round)
        query = (
            "SELECT user_id, follower_id, action FROM follow "
            f"WHERE user_id = ?{time_filter} ORDER BY round ASC"
        )
        data = self.__execute_query(query, (agent_id, *time_params))

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
        :type agent_id: Any
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
            agent_id = next(iter(ydh.agent_mapping()))

            # Get following network for a selected agent
            following_net = ydh.ego_network_following(agent_id=agent_id)
            print(f"Selected agent follows {following_net.number_of_nodes() - 1} accounts")
            print(f"Following IDs: {list(following_net.predecessors(agent_id))}")

            # Compare early vs late following behavior
            early = ydh.ego_network_following(agent_id=agent_id, from_round=0, to_round=500)
            late = ydh.ego_network_following(agent_id=agent_id, from_round=500, to_round=1000)
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
        time_filter, time_params = self.__build_time_filter(from_round, to_round)
        query = (
            "SELECT follower_id, user_id, action FROM follow "
            f"WHERE follower_id = ?{time_filter} ORDER BY round ASC"
        )
        data = self.__execute_query(query, (agent_id, *time_params))

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
        :type agent_id: Any
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
            agent_id = next(iter(ydh.agent_mapping()))

            # Get complete ego network for a selected agent
            ego_net = ydh.ego_network(agent_id=agent_id)
            print(f"Selected agent's ego network has {ego_net.number_of_nodes()} nodes")
            print(f"Edges: {ego_net.number_of_edges()}")

            # Analyze network structure
            in_degree = ego_net.in_degree(agent_id)  # Number of followers
            out_degree = ego_net.out_degree(agent_id)  # Number following
            print(f"Followers: {in_degree}, Following: {out_degree}")

            # Get ego network for specific time period
            period_net = ydh.ego_network(agent_id=agent_id, from_round=100, to_round=500)

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
        :type agent_ids: list[Any], optional
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
        return self.__social_network_graph(
            from_round=from_round, to_round=to_round, agent_ids=agent_ids
        )

    def __social_network_graph(self, from_round=None, to_round=None, agent_ids=None):
        """
        Internal helper that builds the social/follow network without managing
        the database connection lifecycle.
        """
        schema = self.__get_schema()
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "f.round"
        )
        query = (
            "SELECT f.user_id, f.follower_id, f.action "
            "FROM follow AS f"
            f" WHERE 1=1{time_filter} "
            "ORDER BY f.round ASC, f.id ASC"
        )
        rows = self.__execute_query(query, time_params)
        allowed_agents = set(agent_ids) if agent_ids is not None else None
        if allowed_agents is None:
            if schema.has_table("user_mgmt"):
                allowed_agents = {
                    row[0] for row in self.__execute_query("SELECT id FROM user_mgmt")
                }
            else:
                allowed_agents = set()

        actions = defaultdict(list)
        for user_id, follower_id, action in rows:
            if allowed_agents and (
                user_id not in allowed_agents or follower_id not in allowed_agents
            ):
                continue
            actions[(user_id, follower_id)].append(action)

        graph = nx.DiGraph()
        for (source, target), history in actions.items():
            if len(history) % 2 == 1:
                graph.add_edge(source, target)
        return graph

    def __reply_network(self, from_round=None, to_round=None, agent_ids=None):
        """
        Build a directed user-to-user reply network from reply chains.
        """
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            "SELECT p.id, p.user_id, p.comment_to, p.round "
            "FROM post AS p"
            f" WHERE 1=1{time_filter} "
            "ORDER BY p.round ASC, p.id ASC"
        )
        rows = self.__execute_query(query, time_params)
        author_by_post = {row[0]: row[1] for row in rows}
        allowed_agents = set(agent_ids) if agent_ids is not None else None

        edges = defaultdict(int)
        for _post_id, user_id, comment_to, _round in rows:
            if comment_to in (None, -1):
                continue
            parent_author = author_by_post.get(comment_to)
            if parent_author is None:
                continue
            if allowed_agents is not None and (
                user_id not in allowed_agents or parent_author not in allowed_agents
            ):
                continue
            edges[(user_id, parent_author)] += 1

        graph = nx.DiGraph()
        for (source, target), weight in edges.items():
            graph.add_edge(source, target, weight=weight)
        return graph

    def __reaction_network(self, from_round=None, to_round=None, agent_ids=None):
        """
        Build a directed user-to-user reaction network from reaction events.
        """
        schema = self.__get_schema()
        if not schema.has_table("reactions") or not schema.has_table("post"):
            return nx.DiGraph()

        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "r.round"
        )
        query = (
            "SELECT r.user_id, r.post_id "
            "FROM reactions AS r"
            f" WHERE 1=1{time_filter} "
            "ORDER BY r.round ASC, r.id ASC"
        )
        rows = self.__execute_query(query, time_params)
        post_authors = dict(self.__execute_query("SELECT id, user_id FROM post"))
        allowed_agents = set(agent_ids) if agent_ids is not None else None

        edges = defaultdict(int)
        for user_id, post_id in rows:
            target = post_authors.get(post_id)
            if target is None:
                continue
            if allowed_agents is not None and (
                user_id not in allowed_agents or target not in allowed_agents
            ):
                continue
            edges[(user_id, target)] += 1

        graph = nx.DiGraph()
        for (source, target), weight in edges.items():
            graph.add_edge(source, target, weight=weight)
        return graph

    def __recommendation_network(self, from_round=None, to_round=None, agent_ids=None):
        """
        Build a directed user-to-user recommendation exposure network.
        """
        schema = self.__get_schema()
        if not schema.has_table("recommendations") or not schema.has_table("post"):
            return nx.DiGraph()

        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "r.round"
        )
        query = (
            "SELECT r.user_id, r.post_ids "
            "FROM recommendations AS r"
            f" WHERE 1=1{time_filter} "
            "ORDER BY r.round ASC, r.id ASC"
        )
        rows = self.__execute_query(query, time_params)
        post_authors = dict(self.__execute_query("SELECT id, user_id FROM post"))
        allowed_agents = set(agent_ids) if agent_ids is not None else None

        edges = defaultdict(int)
        for user_id, post_ids in rows:
            if not post_ids:
                continue
            for post_id in str(post_ids).split("|"):
                post_id = post_id.strip()
                if not post_id:
                    continue
                target = post_authors.get(post_id)
                if target is None and post_id.isdigit():
                    target = post_authors.get(int(post_id))
                if target is None:
                    continue
                if allowed_agents is not None and (
                    user_id not in allowed_agents or target not in allowed_agents
                ):
                    continue
                edges[(user_id, target)] += 1

        graph = nx.DiGraph()
        for (source, target), weight in edges.items():
            graph.add_edge(source, target, weight=weight)
        return graph

    def __layer_summary(self, graph):
        """
        Summarize a directed graph with a compact metric bundle.
        """
        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()
        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": nx.density(graph) if node_count > 1 else 0.0,
            "reciprocity": nx.reciprocity(graph) if edge_count else 0.0,
            "weight_sum": sum(
                data.get("weight", 1) for _, _, data in graph.edges(data=True)
            ),
        }

    @_handle_db_connection
    def interaction_layers(self, from_round=None, to_round=None, agent_ids=None):
        """
        Return the available user interaction graphs for the current dataset.

        The returned mapping can include:
        - ``follow`` for the social/follow graph
        - ``mention`` for mention interactions
        - ``reply`` for reply-to-author interactions
        - ``reaction`` for reaction-to-author interactions
        - ``recommendation`` for recommendation exposure interactions
        """
        schema = self.__get_schema()
        layers = {}

        if schema.has_table("follow"):
            layers["follow"] = self.__social_network_graph(
                from_round=from_round, to_round=to_round, agent_ids=agent_ids
            )
        if schema.has_table("mentions"):
            layers["mention"] = self.__mention_network_graph(
                from_round=from_round, to_round=to_round, agent_ids=agent_ids
            )
        if schema.has_table("post"):
            layers["reply"] = self.__reply_network(
                from_round=from_round, to_round=to_round, agent_ids=agent_ids
            )
        if schema.has_table("reactions"):
            layers["reaction"] = self.__reaction_network(
                from_round=from_round, to_round=to_round, agent_ids=agent_ids
            )
        if schema.has_table("recommendations"):
            layers["recommendation"] = self.__recommendation_network(
                from_round=from_round, to_round=to_round, agent_ids=agent_ids
            )

        return layers

    @_handle_db_connection
    def multiplex_metrics(self, from_round=None, to_round=None, agent_ids=None):
        """
        Summarize the multiplex interaction layers and their overlaps.
        """
        cached = self.__analysis_cache_get(
            "multiplex_metrics",
            from_round=from_round,
            to_round=to_round,
            agent_ids=tuple(agent_ids) if agent_ids is not None else None,
        )
        if cached is not None:
            return cached

        layers = self.interaction_layers(
            from_round=from_round, to_round=to_round, agent_ids=agent_ids
        )
        layer_metrics = {
            name: self.__layer_summary(graph) for name, graph in layers.items()
        }

        overlap = {}
        layer_names = list(layers.keys())
        for index, left_name in enumerate(layer_names):
            left_edges = set(layers[left_name].edges())
            left_nodes = set(layers[left_name].nodes())
            for right_name in layer_names[index + 1 :]:
                right_edges = set(layers[right_name].edges())
                right_nodes = set(layers[right_name].nodes())
                shared_edges = left_edges & right_edges
                union_edges = left_edges | right_edges
                shared_nodes = left_nodes & right_nodes
                union_nodes = left_nodes | right_nodes
                key = f"{left_name}|{right_name}"
                overlap[key] = {
                    "shared_edge_count": len(shared_edges),
                    "edge_jaccard": (
                        len(shared_edges) / len(union_edges) if union_edges else 0.0
                    ),
                    "shared_node_count": len(shared_nodes),
                    "node_jaccard": (
                        len(shared_nodes) / len(union_nodes) if union_nodes else 0.0
                    ),
                }

        combined = nx.compose_all(list(layers.values())) if layers else nx.DiGraph()
        result = {
            "layer_count": len(layers),
            "available_layers": list(layers.keys()),
            "layer_metrics": layer_metrics,
            "pairwise_overlap": overlap,
            "combined": self.__layer_summary(combined),
        }
        return self.__analysis_cache_set(
            result,
            "multiplex_metrics",
            from_round=from_round,
            to_round=to_round,
            agent_ids=tuple(agent_ids) if agent_ids is not None else None,
        )

    @_handle_db_connection
    def mention_ego_network(self, agent_id, from_round=None, to_round=None):
        """
        Extract the mention ego network for a specific agent.

        Returns a directed weighted network showing which agents the specified
        agent has mentioned in their posts. Edge weights represent the number
        of times each agent was mentioned.

        :param agent_id: The ID of the agent (the "ego")
        :type agent_id: Any
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
            agent_id = next(iter(ydh.agent_mapping()))

            # Get mention network for a selected agent
            mention_net = ydh.mention_ego_network(agent_id=agent_id)
            print(f"Selected agent has mentioned {mention_net.number_of_nodes() - 1} different agents")

            # Analyze mention patterns
            for target in mention_net.successors(agent_id):
                weight = mention_net[agent_id][target]['weight']
                print(f"  Mentioned agent {target}: {weight} times")

            # Compare mention patterns over time
            early_mentions = ydh.mention_ego_network(agent_id=agent_id, from_round=0, to_round=500)
            late_mentions = ydh.mention_ego_network(agent_id=agent_id, from_round=500, to_round=1000)

        See Also:
            :meth:`mention_network`: Get complete mention network for all agents
            :meth:`ego_network`: Get follower/following network
        """
        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            "SELECT m.user_id FROM post as p, mentions as m "
            "WHERE p.user_id = ? AND p.id = m.post_id"
            f"{time_filter}"
        )
        data = self.__execute_query(query, (agent_id, *time_params))

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
        :type agent_ids: list[Any], optional
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
        return self.__mention_network_graph(
            from_round=from_round, to_round=to_round, agent_ids=agent_ids
        )

    def __mention_network_graph(self, from_round=None, to_round=None, agent_ids=None):
        """
        Internal helper that builds the mention network without managing the
        database connection lifecycle.
        """
        schema = self.__get_schema()
        if not schema.has_table("mentions") or not schema.has_table("post"):
            return nx.DiGraph()

        time_filter, time_params = self.__build_time_filter(
            from_round, to_round, "p.round"
        )
        query = (
            "SELECT p.user_id, m.user_id "
            "FROM post AS p, mentions AS m "
            "WHERE p.id = m.post_id"
            f"{time_filter} "
            "ORDER BY p.round ASC, p.id ASC, m.id ASC"
        )
        rows = self.__execute_query(query, time_params)
        allowed_agents = set(agent_ids) if agent_ids is not None else None

        edges = defaultdict(int)
        for source, target in rows:
            if allowed_agents is not None and (
                source not in allowed_agents or target not in allowed_agents
            ):
                continue
            edges[(source, target)] += 1

        graph = nx.DiGraph()
        for (source, target), weight in edges.items():
            graph.add_edge(source, target, weight=weight)
        return graph
