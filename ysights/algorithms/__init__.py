"""
YSights Algorithms
==================

This module provides analysis algorithms for YSocial simulation data.
It includes functions for analyzing agent profiles, detecting social paradoxes,
evaluating recommendation systems, and studying topic dynamics.

Submodules:
    - :mod:`profiles`: Agent profile and interest similarity analysis
    - :mod:`paradox`: Visibility paradox detection and analysis
    - :mod:`recommenders`: Recommendation system metrics and evaluation
    - :mod:`topics`: Topic spread and adoption analysis

Example:
    Using algorithms to analyze simulation data::

        from ysights import YDataHandler
        from ysights.algorithms import (
            profile_topics_similarity,
            visibility_paradox,
            engagement_momentum
        )

        # Initialize data handler
        ydh = YDataHandler('path/to/database.db')
        network = ydh.social_network()

        # Analyze profile similarity
        similarities = profile_topics_similarity(ydh, network)

        # Detect visibility paradox
        paradox = visibility_paradox(ydh, network, N=100)
        print(f"Paradox detected: {paradox['p_value'] < 0.05}")

        # Calculate engagement momentum
        momentum = engagement_momentum(ydh, time_window_rounds=24)

See Also:
    - :mod:`ysights.models`: Data models and database interface
    - :mod:`ysights.viz`: Visualization functions
"""

from .paradox import (
    user_visibility_vs_neighbors,
    visibility_paradox,
    visibility_paradox_population_size_null,
)
from .profiles import profile_topics_similarity
from .recommenders import (
    engagement_momentum,
    personalization_balance_score,
    sentiment_diffusion_metrics,
)
from .topics import adoption_rate, peak_engagement_time, topic_spread
