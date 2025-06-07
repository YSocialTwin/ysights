import unittest
import os
from ysights.models.YDataHandler import YDataHandler
from ysights.algorithms.topics import (
    topic_spread,
    adoption_rate,
    peak_engagement_time,
)


class TopicTestCase(unittest.TestCase):
    @staticmethod
    def get_data_handler():
        # Assuming the database file exists at this path
        db_path = f"{os.sep}example_data{os.sep}ysocial_db.db"

        current_path = os.getcwd().split("ysights")[0] + "ysights" + db_path

        handler = YDataHandler(current_path)
        return handler

    def test_topic_spread(self):
        pass

    def test_topic_peak_engagement_time(self):
        pass

    def test_topic_adoption_rate(self):
        pass


if __name__ == "__main__":
    unittest.main()
