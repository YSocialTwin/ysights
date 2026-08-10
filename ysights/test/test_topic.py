import unittest

from ysights.algorithms.recommenders import sentiment_diffusion_metrics
from ysights.algorithms.topics import adoption_rate, peak_engagement_time, topic_spread


class TopicTestCase(unittest.TestCase):
    def test_topic_spread_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            topic_spread(None)

    def test_topic_peak_engagement_time_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            peak_engagement_time(None)

    def test_topic_adoption_rate_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            adoption_rate(None)

    def test_sentiment_diffusion_metrics_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            sentiment_diffusion_metrics(None)


if __name__ == "__main__":
    unittest.main()
