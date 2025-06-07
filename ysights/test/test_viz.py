import unittest
import os
from matplotlib import pyplot as plt
import plotly
from ysights import algorithms, viz, YDataHandler


class VizTestCase(unittest.TestCase):
    @staticmethod
    def get_data_handler():
        # Assuming the database file exists at this path
        db_path = f"{os.sep}example_data{os.sep}ysocial_db.db"

        current_path = os.getcwd().split("ysights")[0] + "ysights" + db_path

        handler = YDataHandler(current_path)
        return handler

    def test_paradox_density_scatter(self):
        handler = self.get_data_handler()
        network = handler.social_network()
        x, y = algorithms.user_visibility_vs_neighbors(handler, network)
        pl = viz.paradox_density_scatter(
            x, y, xlabel="Impressions", ylabel="Avg. Neighbors Impressions"
        )
        self.assertIsInstance(pl, plt.Figure)

    def test_paradox_histogram(self):
        handler = self.get_data_handler()
        network = handler.social_network()
        data = algorithms.visibility_paradox(handler, network, N=0)
        pl = viz.paradox_histogram(
            data["nodes_coefficients"], bins=30, title="Visibility Paradox Histogram"
        )
        self.assertIsInstance(pl, plt.Figure)

    def test_profile_similarity_distribution(self):
        handler = self.get_data_handler()
        network = handler.social_network()
        r1 = algorithms.profile_topics_similarity(
            handler, network, limit=3, from_round=0, to_round=120
        )
        r2 = algorithms.profile_topics_similarity(
            handler, network, limit=3, from_round=400
        )
        pl = viz.profile_similarity_distribution(
            [r1, r2], ["From 0 to 120", "From 400 to end"]
        )
        self.assertIsInstance(pl, plt.Figure)

    def test_profile_similarity_vs_degree(self):
        handler = self.get_data_handler()
        network = handler.social_network()
        r1 = algorithms.profile_topics_similarity(
            handler, network, limit=3, from_round=0, to_round=120
        )
        g1 = handler.social_network(from_round=0, to_round=120)
        r2 = algorithms.profile_topics_similarity(
            handler, network, limit=3, from_round=400
        )
        g2 = handler.social_network(from_round=400)
        pl = viz.profile_similarity_vs_degree(
            [r1, r2], [g1, g2], ["From 0 to 120", "From 400 to end"]
        )
        self.assertIsInstance(pl, plt.Figure)

    def test_binned_similarity_per_degree(self):
        handler = self.get_data_handler()
        network = handler.social_network()
        r1 = algorithms.profile_topics_similarity(
            handler, network, limit=3, from_round=0, to_round=120
        )
        g1 = handler.social_network(from_round=0, to_round=120)
        r2 = algorithms.profile_topics_similarity(
            handler, network, limit=3, from_round=400
        )
        g2 = handler.social_network(from_round=400)
        pl = viz.binned_similarity_per_degree(
            [r1, r2], [g1, g2], ["From 0 to 120", "From 400 to end"], bins=10
        )
        self.assertIsInstance(pl, plt.Figure)

    def test_topic_density_temporal_evolution(self):
        handler = self.get_data_handler()
        pl = viz.topic_density_temporal_evolution(handler)
        self.assertIsInstance(pl, plotly.graph_objs.Figure)


if __name__ == "__main__":
    unittest.main()
