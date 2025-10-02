import os
import unittest

from ysights.algorithms.paradox import (
    visibility_paradox,
    visibility_paradox_population_size_null,
)
from ysights.algorithms.profiles import profile_topics_similarity
from ysights.models.YDataHandler import YDataHandler


class AlgosTestCase(unittest.TestCase):
    @staticmethod
    def get_data_handler():
        # Assuming the database file exists at this path
        db_path = (
            f"{os.sep}example_data{os.sep}RC_ER_database_server.db"  # ysocial_db.db"
        )

        current_path = os.getcwd().split("ysights")[0] + "ysights" + db_path

        handler = YDataHandler(current_path)
        return handler

    def test_paradox_algorithm(self):
        handler = self.get_data_handler()
        network = handler.social_network()

        results = visibility_paradox(handler, network, N=10)
        self.assertIsInstance(results, dict)
        self.assertIn("z_score", results)
        self.assertIn("p_value", results)
        self.assertIn("nodes_coefficients", results)
        self.assertIn("paradox_score", results)
        print(results["paradox_score"], results["p_value"])

    def test_paradox_population_size_null(self):
        handler = self.get_data_handler()
        network = handler.social_network()

        results = visibility_paradox_population_size_null(handler, network, N=2)
        self.assertIsInstance(results, dict)

    def test_profile_similarity(self):
        handler = self.get_data_handler()
        network = handler.social_network()

        results = profile_topics_similarity(handler, network)
        self.assertIsInstance(results, dict)
        print(results)
