"""
YSights Visualization
=====================

This module provides visualization functions for YSocial simulation data.
It includes plotting functions for paradox analysis, profile similarity,
topic evolution, global trends, and recommendation system metrics.

Submodules:
    - :mod:`paradox_viz`: Visibility paradox visualizations
    - :mod:`profiles_viz`: Agent profile and similarity visualizations
    - :mod:`topics_viz`: Topic density and evolution visualizations
    - :mod:`global_trends`: Aggregate statistics and trends
    - :mod:`recommendations`: Recommendation system visualizations

Example:
    Creating visualizations::

        from ysights import YDataHandler
        from ysights.algorithms import visibility_paradox, profile_topics_similarity
        from ysights.viz import (
            paradox_histogram,
            profile_similarity_distribution,
            topic_density_temporal_evolution,
            daily_contents_trends
        )
        
        # Initialize data handler
        ydh = YDataHandler('path/to/database.db')
        network = ydh.social_network()
        
        # Visualize paradox
        paradox_results = visibility_paradox(ydh, network, N=100)
        fig = paradox_histogram(paradox_results)
        fig.show()
        
        # Visualize profile similarity
        similarities = profile_topics_similarity(ydh, network)
        fig = profile_similarity_distribution(similarities)
        fig.show()
        
        # Visualize topic evolution
        fig = topic_density_temporal_evolution(ydh, min_days=15)
        fig.show()
        
        # Show daily content trends
        fig = daily_contents_trends(ydh)
        fig.show()

Note:
    Most visualization functions return Plotly figure objects that can be
    displayed with `.show()`, saved with `.write_html()`, or further customized.

See Also:
    - :mod:`ysights.algorithms`: Analysis algorithms that generate data for plots
    - :mod:`ysights.models`: Data models and database interface
"""
from .paradox_viz import paradox_density_scatter, paradox_histogram, paradox_size_impact
from .profiles_viz import (
    profile_similarity_distribution,
    profile_similarity_vs_degree,
    binned_similarity_per_degree,
)
from .topics_viz import topic_density_temporal_evolution
from .global_trends import (
    daily_contents_trends,
    contents_per_user_distributions,
    daily_reactions_trends,
    trending_hashtags,
    trending_emotions,
    tending_topics,
    comments_per_post_distribution,
)
from .recommendations import (
    recommendations_per_post_distribution,
    recommendations_vs_reactions,
    recommendations_vs_comments,
)
