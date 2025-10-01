"""
ySights - YSocial Data Analysis Library
========================================

ySights is a Python library for analyzing data from YSocial simulations.
It provides tools for extracting insights from social media simulation data,
including agent behaviors, content dynamics, network structures, and
recommendation system effects.

Main Components:
    - **models**: Data models and database interface (YDataHandler, Agent, Post)
    - **algorithms**: Analysis algorithms (profiles, paradox, recommenders, topics)
    - **viz**: Visualization functions for simulation results

Quick Start:
    Basic usage example::

        from ysights import YDataHandler

        # Initialize data handler
        ydh = YDataHandler('path/to/simulation.db')

        # Get simulation time range
        time_range = ydh.time_range()
        print(f"Simulation: rounds {time_range['min_round']} to {time_range['max_round']}")

        # Get all agents
        agents = ydh.agents()
        print(f"Total agents: {len(agents.get_agents())}")

        # Extract social network
        network = ydh.social_network()
        print(f"Network: {network.number_of_nodes()} nodes, {network.number_of_edges()} edges")

Modules:
    - :mod:`ysights.models`: Core data models and database interface
    - :mod:`ysights.algorithms`: Analysis and metric calculation
    - :mod:`ysights.viz`: Visualization and plotting functions

See Also:
    - YSocial Simulation Platform: https://github.com/YSocialTwin
    - Documentation: https://github.com/YSocialTwin/ysights
"""

from .models import YDataHandler
