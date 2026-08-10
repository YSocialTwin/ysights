import unittest

from ysights.algorithms.recommenders import sentiment_diffusion_metrics
from ysights.algorithms.topics import adoption_rate, peak_engagement_time, topic_spread
from ysights.models.YDataHandler import YDataHandler
from ysights.test.test_regressions import _create_fixture_db


class TopicTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir, cls.db_path = _create_fixture_db()

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def get_data_handler(self):
        return YDataHandler(self.db_path)

    def test_topic_spread_returns_topic_summaries(self):
        handler = self.get_data_handler()
        spread = topic_spread(handler)

        self.assertIsInstance(spread, dict)
        self.assertGreater(len(spread), 0)

        first_topic_id = next(iter(spread))
        summary = spread[first_topic_id]
        self.assertIn("timeline", summary)
        self.assertIn("peak_period", summary)
        self.assertIn("adoption_rate", summary)
        self.assertIn("post_count", summary)

    def test_topic_adoption_rate_returns_values(self):
        handler = self.get_data_handler()
        rates = adoption_rate(handler)

        self.assertIsInstance(rates, dict)
        self.assertGreater(len(rates), 0)
        for value in rates.values():
            self.assertIsInstance(value, float)
            self.assertGreaterEqual(value, 0.0)

    def test_topic_peak_engagement_time_returns_values(self):
        handler = self.get_data_handler()
        peaks = peak_engagement_time(handler)

        self.assertIsInstance(peaks, dict)
        self.assertGreater(len(peaks), 0)
        for value in peaks.values():
            self.assertIsNotNone(value)

    def test_sentiment_diffusion_metrics_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            sentiment_diffusion_metrics(None)


if __name__ == "__main__":
    unittest.main()
