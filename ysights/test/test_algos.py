import unittest
import os
from ysights.models.YDataHandler import YDataHandler
from ysights.algorithms.paradox import visibility_paradox


class AlgosTestCase(unittest.TestCase):
    @staticmethod
    def get_data_handler():
        # Assuming the database file exists at this path
        db_path = f"{os.sep}example_data{os.sep}ysocial_db.db"

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



