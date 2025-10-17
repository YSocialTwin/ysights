ySights Documentation
=====================

ySights is a Python library for analyzing data from YSocial simulations.
It provides tools for extracting insights from social media simulation data,
including agent behaviors, content dynamics, network structures, and
recommendation system effects.

Features
--------

* **Data Models**: Comprehensive data models for agents, posts, and simulation data
* **Network Analysis**: Social network extraction and analysis capabilities
* **Algorithm Library**: Profile analysis, paradox detection, and recommendation metrics
* **Visualization Tools**: Rich visualization functions for simulation insights
* **Sphinx Documentation**: Complete API reference with examples

Quick Start
-----------

.. code-block:: python

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

Installation
------------

.. code-block:: bash

    pip install ysights

or from source:

.. code-block:: bash

    git clone https://github.com/YSocialTwin/ysights.git
    cd ysights
    pip install -e .

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials

.. toctree::
   :maxdepth: 2
   :caption: Module Documentation

   modules/models
   modules/algorithms
   modules/viz


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`