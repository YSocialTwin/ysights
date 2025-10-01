"""
YSocial Data Models
===================

This module provides data model classes for working with YSocial simulation data.
It includes classes for agents, posts, and the main data handler for database operations.

Classes:
    - Agent: Individual agent/user in the simulation
    - Agents: Collection of Agent objects
    - Post: Individual post/message in the simulation
    - Posts: Collection of Post objects
    - YDataHandler: Main interface for database operations and data retrieval

Example:
    Basic usage of data models::

        from ysights.models import YDataHandler, Agent, Post

        # Initialize data handler
        ydh = YDataHandler('path/to/database.db')

        # Get all agents
        agents = ydh.agents()
        for agent in agents.get_agents():
            print(f"Agent {agent.id}: {agent.username}")

        # Get posts by agent with enrichment
        posts = ydh.posts_by_agent(agent_id=5, enrich_dimensions=['sentiment', 'hashtags'])
        for post in posts.get_posts():
            print(f"Post: {post.text}")
            print(f"Sentiment: {post.sentiment}")

See Also:
    - :mod:`ysights.algorithms`: Analysis algorithms
    - :mod:`ysights.viz`: Visualization functions
"""

from .Agents import Agent, Agents
from .Posts import Post, Posts
from .YDataHandler import YDataHandler
