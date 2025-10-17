import os
import sqlite3
import subprocess
import tempfile
import unittest

try:
    import psycopg2
    import psycopg2.extensions

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

import networkx as nx

from ysights.models.YDataHandler import Agent, Agents, Post, Posts, YDataHandler


@unittest.skipIf(not PSYCOPG2_AVAILABLE, "psycopg2 not available")
class PostgreSQLIntegrationTestCase(unittest.TestCase):
    """
    Integration tests for PostgreSQL support.

    This test creates a temporary PostgreSQL database, copies data from
    the SQLite test database, and runs queries to verify functionality.
    """

    @classmethod
    def setUpClass(cls):
        """Set up a temporary PostgreSQL database for testing."""
        cls.sqlite_db_path = None
        cls.pg_conn = None
        cls.pg_dbname = None

        try:
            # Get SQLite database path
            db_path = f"{os.sep}example_data{os.sep}ysocial_db.db"
            cls.sqlite_db_path = os.getcwd().split("ysights")[0] + "ysights" + db_path

            if not os.path.exists(cls.sqlite_db_path):
                raise unittest.SkipTest(
                    f"SQLite database not found at {cls.sqlite_db_path}"
                )

            # Create a unique database name for this test
            import random

            cls.pg_dbname = f"ysights_test_{random.randint(1000, 9999)}"

            # Try to connect to PostgreSQL (default postgres database)
            try:
                conn = psycopg2.connect(
                    dbname="postgres",
                    user=os.environ.get("PGUSER", "postgres"),
                    password=os.environ.get("PGPASSWORD", "password"),
                    host=os.environ.get("PGHOST", "localhost"),
                    port=os.environ.get("PGPORT", "5432"),
                )
                conn.autocommit = True
                cursor = conn.cursor()

                # Create test database
                cursor.execute(f"DROP DATABASE IF EXISTS {cls.pg_dbname}")
                cursor.execute(f"CREATE DATABASE {cls.pg_dbname}")
                cursor.close()
                conn.close()

                # Connect to the new database
                cls.pg_conn = psycopg2.connect(
                    dbname=cls.pg_dbname,
                    user=os.environ.get("PGUSER", "postgres"),
                    password=os.environ.get("PGPASSWORD", "password"),
                    host=os.environ.get("PGHOST", "localhost"),
                    port=os.environ.get("PGPORT", "5432"),
                )
                cls.pg_conn.autocommit = True

                # Copy schema and data from SQLite to PostgreSQL
                cls._copy_sqlite_to_postgresql()

            except psycopg2.OperationalError as e:
                raise unittest.SkipTest(f"Cannot connect to PostgreSQL: {e}")

        except Exception as e:
            raise unittest.SkipTest(f"Failed to set up PostgreSQL test database: {e}")

    @classmethod
    def _copy_sqlite_to_postgresql(cls):
        """Copy schema and data from SQLite to PostgreSQL."""
        # This is a simplified version that copies a few key tables
        sqlite_conn = sqlite3.connect(cls.sqlite_db_path)
        pg_cursor = cls.pg_conn.cursor()

        # Create tables in PostgreSQL (simplified schema)
        tables_to_copy = [
            (
                "user_mgmt",
                """
                CREATE TABLE user_mgmt (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    password VARCHAR(200) NOT NULL,
                    user_type TEXT,
                    leaning TEXT,
                    age INTEGER,
                    oe TEXT,
                    co TEXT,
                    ex TEXT,
                    ag TEXT,
                    ne TEXT,
                    recsys_type TEXT,
                    language TEXT,
                    owner TEXT,
                    education_level TEXT,
                    joined_on INTEGER,
                    frecsys_type TEXT,
                    round_actions INTEGER DEFAULT 3 NOT NULL,
                    gender TEXT,
                    nationality TEXT,
                    toxicity TEXT,
                    is_page INTEGER DEFAULT 0 NOT NULL,
                    left_on INTEGER,
                    daily_activity_level INTEGER DEFAULT 1,
                    profession TEXT
                )
            """,
            ),
            (
                "rounds",
                """
                CREATE TABLE rounds (
                    id INTEGER PRIMARY KEY,
                    day INTEGER,
                    hour INTEGER
                )
            """,
            ),
            (
                "post",
                """
                CREATE TABLE post (
                    id INTEGER PRIMARY KEY,
                    tweet TEXT NOT NULL,
                    post_img VARCHAR(20),
                    user_id INTEGER NOT NULL REFERENCES user_mgmt(id),
                    comment_to INTEGER DEFAULT -1,
                    thread_id INTEGER,
                    round INTEGER REFERENCES rounds(id),
                    news_id INTEGER DEFAULT -1,
                    shared_from INTEGER DEFAULT -1,
                    image_id INTEGER
                )
            """,
            ),
        ]

        for table_name, create_sql in tables_to_copy:
            try:
                pg_cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                pg_cursor.execute(create_sql)

                # Copy data
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f"SELECT * FROM {table_name}")
                rows = sqlite_cursor.fetchall()

                if rows:
                    # Get column names
                    columns = [desc[0] for desc in sqlite_cursor.description]
                    placeholders = ", ".join(["%s"] * len(columns))
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                    pg_cursor.executemany(insert_sql, rows)

            except Exception as e:
                print(f"Warning: Could not copy table {table_name}: {e}")

        sqlite_conn.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up the temporary PostgreSQL database."""
        if cls.pg_conn:
            cls.pg_conn.close()

        if cls.pg_dbname:
            try:
                conn = psycopg2.connect(
                    dbname="dashboard",
                    user=os.environ.get("PGUSER", "postgres"),
                    password=os.environ.get("PGPASSWORD", ""),
                    host=os.environ.get("PGHOST", "localhost"),
                    port=os.environ.get("PGPORT", "5432"),
                )
                conn.autocommit = True
                cursor = conn.cursor()
                cursor.execute(f"DROP DATABASE IF EXISTS {cls.pg_dbname}")
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Warning: Could not clean up test database: {e}")

    def get_postgresql_handler(self):
        """Get a YDataHandler for the PostgreSQL test database."""
        connection_string = (
            f"postgresql://{os.environ.get('PGUSER', 'postgres')}:"
            f"{os.environ.get('PGPASSWORD', 'password')}@"
            f"{os.environ.get('PGHOST', 'localhost')}:"
            f"{os.environ.get('PGPORT', '5432')}/"
            f"{self.pg_dbname}"
        )
        return YDataHandler(connection_string)

    def test_postgresql_connection(self):
        """Test basic PostgreSQL connection."""
        handler = self.get_postgresql_handler()
        self.assertEqual(handler.db_type, "postgresql")

    def test_get_agents_postgresql(self):
        """Test retrieving agents from PostgreSQL."""
        handler = self.get_postgresql_handler()
        agents = handler.agents()

        self.assertIsInstance(agents, Agents)
        self.assertGreater(len(agents.get_agents()), 0)

        for agent in agents.get_agents():
            self.assertIsInstance(agent, Agent)

    def test_get_number_of_agents_postgresql(self):
        """Test counting agents in PostgreSQL."""
        handler = self.get_postgresql_handler()
        num_agents = handler.number_of_agents()

        self.assertIsInstance(num_agents, int)
        self.assertGreater(num_agents, 0)

    def test_agent_mapping_postgresql(self):
        """Test agent mapping in PostgreSQL."""
        handler = self.get_postgresql_handler()
        agent_mapping = handler.agent_mapping()

        self.assertIsInstance(agent_mapping, dict)
        self.assertGreater(len(agent_mapping), 0)

        for key, value in agent_mapping.items():
            self.assertIsInstance(key, int)
            self.assertIsInstance(value, str)

    def test_time_range_postgresql(self):
        """Test time range query in PostgreSQL."""
        handler = self.get_postgresql_handler()
        time_info = handler.time_range()

        self.assertIsInstance(time_info, dict)
        self.assertIn("min_round", time_info)
        self.assertIn("max_round", time_info)
        self.assertIsInstance(time_info["min_round"], int)
        self.assertIsInstance(time_info["max_round"], int)

    def test_posts_postgresql(self):
        """Test retrieving posts from PostgreSQL."""
        handler = self.get_postgresql_handler()
        posts = handler.posts()

        self.assertIsInstance(posts, Posts)
        self.assertGreater(len(posts.get_posts()), 0)

        for post in posts.get_posts()[:5]:  # Check first 5 posts
            self.assertIsInstance(post, Post)

    def test_custom_query_postgresql(self):
        """Test custom query execution in PostgreSQL."""
        handler = self.get_postgresql_handler()

        query = "SELECT * FROM user_mgmt WHERE id = 1"
        result = handler.custom_query(query)

        self.assertIsInstance(result, list)
        if result:
            self.assertIsInstance(result[0], tuple)


if __name__ == "__main__":
    unittest.main()
