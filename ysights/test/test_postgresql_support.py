import os
import sqlite3
import unittest

from ysights.models.YDataHandler import YDataHandler


class PostgreSQLSupportTestCase(unittest.TestCase):
    """
    Test PostgreSQL support by verifying query conversion and initialization.

    Note: This test does not require an actual PostgreSQL database.
    It tests the initialization and query conversion logic.
    """

    def test_sqlite_initialization(self):
        """Test that SQLite databases are correctly identified."""
        db_path = f"{os.sep}example_data{os.sep}ysocial_db.db"
        current_path = os.getcwd().split("ysights")[0] + "ysights" + db_path

        handler = YDataHandler(current_path)
        self.assertEqual(handler.db_type, "sqlite")
        self.assertEqual(handler.db_path, current_path)

    def test_postgresql_initialization(self):
        """Test that PostgreSQL connection strings are correctly identified."""
        # Test with postgresql:// prefix
        handler = YDataHandler(
            "postgresql://postgresql:password@localhost:5432/test_db"
        )
        self.assertEqual(handler.db_type, "postgresql")

        # Test with postgres:// prefix
        handler2 = YDataHandler("postgres://user:password@localhost:5432/test_db")
        self.assertEqual(handler2.db_type, "postgresql")

    def test_query_conversion_sqlite(self):
        """Test that SQLite queries remain unchanged."""
        db_path = f"{os.sep}example_data{os.sep}ysocial_db.db"
        current_path = os.getcwd().split("ysights")[0] + "ysights" + db_path

        handler = YDataHandler(current_path)

        # Test query with placeholders
        query = "SELECT * FROM user_mgmt WHERE id = ? AND age > ?"
        params = (1, 25)

        converted_query, converted_params = handler._YDataHandler__convert_query_for_db(
            query, params
        )

        # SQLite should not change the query
        self.assertEqual(converted_query, query)
        self.assertEqual(converted_params, params)

    def test_query_conversion_postgresql(self):
        """Test that PostgreSQL queries are converted correctly."""
        handler = YDataHandler(
            "postgresql://postgresql:password@localhost:5432/test_db"
        )

        # Test query with placeholders
        query = "SELECT * FROM user_mgmt WHERE id = ? AND age > ?"
        params = (1, 25)

        converted_query, converted_params = handler._YDataHandler__convert_query_for_db(
            query, params
        )

        # PostgreSQL should convert ? to %s
        expected_query = "SELECT * FROM user_mgmt WHERE id = %s AND age > %s"
        self.assertEqual(converted_query, expected_query)
        self.assertEqual(converted_params, params)

    def test_query_conversion_complex(self):
        """Test query conversion with complex queries."""
        handler = YDataHandler(
            "postgresql://postgresql:password@localhost:5432/test_db"
        )

        # Test query with multiple placeholders
        query = "SELECT * FROM post WHERE user_id = ? AND round >= ? AND round <= ?"
        params = (5, 100, 200)

        converted_query, converted_params = handler._YDataHandler__convert_query_for_db(
            query, params
        )

        expected_query = (
            "SELECT * FROM post WHERE user_id = %s AND round >= %s AND round <= %s"
        )
        self.assertEqual(converted_query, expected_query)
        self.assertEqual(converted_params, params)

    def test_query_conversion_no_params(self):
        """Test query conversion without parameters."""
        handler = YDataHandler(
            "postgresql://postgresql:password@localhost:5432/test_db"
        )

        query = "SELECT * FROM user_mgmt"
        params = None

        converted_query, converted_params = handler._YDataHandler__convert_query_for_db(
            query, params
        )

        # Query without placeholders should remain unchanged
        self.assertEqual(converted_query, query)
        self.assertEqual(converted_params, params)


if __name__ == "__main__":
    unittest.main()
