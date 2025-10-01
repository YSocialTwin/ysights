Tutorials
=========

Interactive Jupyter notebook tutorials demonstrating ySights functionality.

.. toctree::
   :maxdepth: 2
   :caption: Tutorial Notebooks

   tutorials/01_getting_started
   tutorials/02_network_analysis
   tutorials/03_algorithms
   tutorials/04_visualization

Overview
--------

The ySights tutorials provide hands-on examples for analyzing YSocial simulation data. Each notebook is self-contained with detailed explanations and runnable code examples.

Getting Started
---------------

**Prerequisites:**

.. code-block:: bash

   pip install ysights jupyter matplotlib numpy scipy networkx plotly

**Running Notebooks:**

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/YSocialTwin/ysights.git
      cd ysights

2. Start Jupyter:

   .. code-block:: bash

      jupyter notebook docs/notebooks/

3. Open any notebook and update the database path to your simulation file

Tutorial Contents
-----------------

1. Getting Started with ySights
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Introduction to basic ySights functionality:

- Initializing the YDataHandler
- Loading and exploring simulation data  
- Working with Agents and Posts
- Basic queries and visualizations
- Agent interest profiles

**Topics Covered:** Data loading, agent filtering, post retrieval, custom queries

2. Network Analysis
~~~~~~~~~~~~~~~~~~~

Social network extraction and analysis:

- Extracting social and mention networks
- Computing network metrics (density, degree distribution)
- Centrality measures (degree, betweenness)
- Ego network analysis
- Community detection
- Network visualization

**Topics Covered:** Graph analysis, centrality, communities, visualization

3. Algorithms
~~~~~~~~~~~~~

Advanced analytical algorithms:

- Profile similarity analysis
- Visibility paradox detection
- Recommendation system metrics
- Topic dynamics analysis

**Topics Covered:** Profile analysis, paradox detection, engagement metrics, topic spread

4. Visualization
~~~~~~~~~~~~~~~~

Creating publication-ready visualizations:

- Global trends (daily activity, hashtags, emotions)
- Topic evolution plots
- Profile similarity visualizations
- Paradox density plots
- Recommendation system analysis
- Custom dashboards

**Topics Covered:** Plotting, dashboards, publication-quality figures

Learning Path
-------------

**Recommended Order:**

1. **Getting Started** - Master the basics of data loading and exploration
2. **Network Analysis** - Learn to extract and analyze social networks
3. **Algorithms** - Explore advanced analytical methods
4. **Visualization** - Create compelling visualizations of your results

Each notebook builds on concepts from previous ones, so following this order provides the best learning experience.

Tips for Success
----------------

- Run code cells sequentially (use Shift+Enter)
- Modify parameters to explore your specific data
- Read all markdown cells for context and explanations
- Save modified notebooks with different names to preserve examples
- Experiment with different visualization styles

Next Steps
----------

After completing the tutorials:

- Apply these techniques to your own simulation data
- Combine multiple analyses for comprehensive insights
- Create custom analyses tailored to your research questions
- Explore the :doc:`api` for additional functionality

Resources
---------

- `Download Notebooks <https://github.com/YSocialTwin/ysights/tree/main/docs/notebooks>`_
- :doc:`api` - Complete API reference
- :doc:`index` - Main documentation
- `GitHub Repository <https://github.com/YSocialTwin/ysights>`_
