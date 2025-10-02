import os
import unittest

import plotly
from matplotlib import pyplot as plt

from ysights import YDataHandler, algorithms, viz


class VizTestCase(unittest.TestCase):
    @staticmethod
    def get_data_handler():
        # Assuming the database file exists at this path
        db_path = (
            f"{os.sep}example_data{os.sep}RC_ER_database_server.db"  # ysocial_db.db"
        )

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

    def test_paradox_size_impact(self):
        handler = self.get_data_handler()
        network = handler.social_network()

        results = algorithms.visibility_paradox_population_size_null(
            handler,
            network,
            N=30,
            subject_to_rec=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.95],
        )

        pl = viz.paradox_size_impact(results)
        self.assertIsInstance(pl, plt.Figure)
        pl.show()

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

    def test_daily_contents_trends(self):
        handler = self.get_data_handler()
        pl = viz.daily_contents_trends(handler)
        self.assertIsInstance(pl, plt.Figure)

    def test_daily_reactions_trends(self):
        handler = self.get_data_handler()
        pl = viz.daily_reactions_trends(handler)
        self.assertIsInstance(pl, plt.Figure)
        pl = viz.daily_reactions_trends(handler, smooth_days=7)
        self.assertIsInstance(pl, plt.Figure)

    def test_contents_per_user_distributions(self):
        handler = self.get_data_handler()
        pl = viz.contents_per_user_distributions(handler)
        self.assertIsInstance(pl, plt.Figure)

    def test_trending_hashtags(self):
        handler = self.get_data_handler()
        pl = viz.trending_hashtags(handler)
        self.assertIsInstance(pl, plt.Figure)

    def test_trending_emotions(self):
        handler = self.get_data_handler()
        pl = viz.trending_emotions(handler)
        self.assertIsInstance(pl, plt.Figure)

    def test_trending_topics(self):
        handler = self.get_data_handler()
        pl = viz.tending_topics(handler)
        self.assertIsInstance(pl, plt.Figure)

    def test_comments_per_post_distribution(self):
        handler = self.get_data_handler()
        pl = viz.comments_per_post_distribution(handler)
        self.assertIsInstance(pl, plt.Figure)

    def test_recommendations_per_post_distribution(self):
        handler = self.get_data_handler()
        pl = viz.recommendations_per_post_distribution(handler)
        self.assertIsInstance(pl, plt.Figure)

    def test_recommendations_vs_reactions(self):
        handler = self.get_data_handler()
        pl = viz.recommendations_vs_reactions(handler)
        self.assertIsInstance(pl, plt.Figure)
        pl = viz.recommendations_vs_reactions(handler, density=True)
        self.assertIsInstance(pl, plt.Figure)

    def test_recommendations_vs_comments(self):
        handler = self.get_data_handler()
        pl = viz.recommendations_vs_comments(handler)
        self.assertIsInstance(pl, plt.Figure)
        pl = viz.recommendations_vs_comments(handler, density=True)
        self.assertIsInstance(pl, plt.Figure)


if __name__ == "__main__":
    unittest.main()
