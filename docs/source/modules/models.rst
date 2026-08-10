Models Package
==============

The models package provides core data structures and the main database interface
for working with YSocial simulation data.

YDataHandler
------------

The main interface for database operations and data retrieval.
It now includes analytical helpers for:

* schema discovery and capability detection
* thread reconstruction and conversation metrics
* activity timelines and burst detection
* topic lifecycle summaries and semantic profiles
* user profile summaries, drift, and segmentation
* moderation summaries, forum session summaries, and reporting exports
* cache inspection and performance hardening utilities

.. automodule:: ysights.models.YDataHandler
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:

Agent Classes
-------------

Classes for representing individual agents and agent collections.

.. automodule:: ysights.models.Agents
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:

Post Classes
------------

Classes for representing posts and post collections.

.. automodule:: ysights.models.Posts
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
