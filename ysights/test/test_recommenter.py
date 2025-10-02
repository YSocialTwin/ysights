import os
import unittest

from ysights.algorithms.recommenders import (
    engagement_momentum,
    personalization_balance_score,
)
from ysights.models.YDataHandler import YDataHandler


class RecsysTestCase(unittest.TestCase):
    @staticmethod
    def get_data_handler():
        # Assuming the database file exists at this path
        db_path = f"{os.sep}example_data{os.sep}ysocial_db.db"

        current_path = os.getcwd().split("ysights")[0] + "ysights" + db_path

        handler = YDataHandler(current_path)
        return handler

    def test_engagement_momentum(self):
        handler = self.get_data_handler()
        res = engagement_momentum(handler)
        self.assertIsInstance(res, dict)

    def test_personalization_balance_score(self):
        handler = self.get_data_handler()
        res = personalization_balance_score(handler)
        self.assertIsInstance(res, dict)
