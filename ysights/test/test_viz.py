import unittest
import os

from matplotlib import pyplot as plt

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
        pl = viz.paradox_density_scatter(x, y, xlabel='Impressions', ylabel='Avg. Neighbors Impressions')
        self.assertIsInstance(pl, plt.Figure)

    def test_paradox_histogram(self):
        handler = self.get_data_handler()
        network = handler.social_network()
        data = algorithms.visibility_paradox(handler, network, N=0)
        pl = viz.paradox_histogram(data["nodes_coefficients"], bins=30, title='Visibility Paradox Histogram')
        self.assertIsInstance(pl, plt.Figure)


if __name__ == '__main__':
    unittest.main()
