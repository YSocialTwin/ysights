import os
import unittest

from ysights.algorithms.paradox import (
    visibility_paradox,
    visibility_paradox_population_size_null,
    visibility_paradox_per_degree_class,
    visibility_paradox_temporal,
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

    def test_paradox_per_degree_class(self):
        handler = self.get_data_handler()
        network = handler.social_network()

        # Test with default linear binning
        results = visibility_paradox_per_degree_class(handler, network, N=10, num_bins=5)
        self.assertIsInstance(results, dict)
        self.assertIn("bin_edges", results)
        self.assertIn("bin_centers", results)
        self.assertIn("paradox_scores", results)
        self.assertIn("z_scores", results)
        self.assertIn("p_values", results)
        self.assertIn("bin_counts", results)
        
        # Check that arrays have expected length
        self.assertEqual(len(results["bin_centers"]), 5)
        self.assertEqual(len(results["paradox_scores"]), 5)
        self.assertEqual(len(results["z_scores"]), 5)
        self.assertEqual(len(results["p_values"]), 5)
        self.assertEqual(len(results["bin_counts"]), 5)
        
        print(f"Bin centers: {results['bin_centers']}")
        print(f"Paradox scores: {results['paradox_scores']}")
        print(f"P-values: {results['p_values']}")

    def test_paradox_per_degree_class_custom_bins(self):
        handler = self.get_data_handler()
        network = handler.social_network()

        # Test with custom bins
        custom_bins = [0, 5, 10, 20, 50, 100]
        results = visibility_paradox_per_degree_class(handler, network, N=10, bins=custom_bins)
        self.assertIsInstance(results, dict)
        self.assertIn("bin_edges", results)
        
        # Check that we have the right number of bins
        expected_num_bins = len(custom_bins) - 1
        self.assertEqual(len(results["bin_centers"]), expected_num_bins)
        
        print(f"Custom bins - Bin centers: {results['bin_centers']}")
        print(f"Custom bins - Paradox scores: {results['paradox_scores']}")

    def test_profile_similarity(self):
        handler = self.get_data_handler()
        network = handler.social_network()

        results = profile_topics_similarity(handler, network)
        self.assertIsInstance(results, dict)
        print(results)

    def test_paradox_temporal(self):
        handler = self.get_data_handler()
        network = handler.social_network()

        # Test with 1 day granularity
        results = visibility_paradox_temporal(handler, network, temporal_granularity=(1, 0), N=5)
        self.assertIsInstance(results, dict)
        self.assertIn("time_points", results)
        self.assertIn("paradox_scores", results)
        self.assertIn("z_scores", results)
        self.assertIn("p_values", results)
        self.assertIn("temporal_granularity", results)
        
        # Check that arrays have expected properties
        self.assertEqual(len(results["time_points"]), len(results["paradox_scores"]))
        self.assertEqual(len(results["paradox_scores"]), len(results["z_scores"]))
        self.assertEqual(len(results["z_scores"]), len(results["p_values"]))
        
        print(f"Temporal paradox computed for {len(results['time_points'])} time windows")
        print(f"Temporal granularity: {results['temporal_granularity']}")
        if len(results['time_points']) > 0:
            print(f"First time point: Day {results['time_points'][0][0]}, Hour {results['time_points'][0][1]}")
            print(f"First paradox score: {results['paradox_scores'][0]:.4f}")

    def test_paradox_temporal_custom_granularity(self):
        handler = self.get_data_handler()
        network = handler.social_network()

        # Test with 12 hour granularity
        results = visibility_paradox_temporal(handler, network, temporal_granularity=(0, 12), N=5)
        self.assertIsInstance(results, dict)
        self.assertEqual(results['temporal_granularity'], (0, 12))
        
        print(f"Custom granularity (12h) - Time windows: {len(results['time_points'])}")
