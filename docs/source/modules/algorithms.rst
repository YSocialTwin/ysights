Algorithms Package
==================

The algorithms package provides analysis functions for YSocial simulation data,
including profile similarity, recommendation metrics, topic lifecycle analysis,
and higher-level content dynamics helpers.

Profile Analysis
----------------

Functions for analyzing agent profiles and interest similarity.

.. automodule:: ysights.algorithms.profiles
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:

Recommender Metrics
-------------------

Metrics for evaluating recommendation system performance.

.. automodule:: ysights.algorithms.recommenders
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:

Topic Analysis
--------------

Functions for analyzing topic dynamics and evolution.
The topic module now exposes implemented lifecycle entry points rather than
placeholders.

.. automodule:: ysights.algorithms.topics
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:

Performance and Reporting
-------------------------

The recommendation and reporting helpers are documented through the model
layer, which now exposes cached summaries, exports, and benchmark utilities.
