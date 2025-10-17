![ysigth.png](docs/source/ysigth.png)
# ySights - YSocial Data Analysis Made Simple
[![PyPI Version](https://img.shields.io/pypi/v/ysights.svg)](https://pypi.org/project/ysights/)
[![CI - Code Quality and Tests](https://github.com/YSocialTwin/ysights/actions/workflows/ci.yml/badge.svg)](https://github.com/YSocialTwin/ysights/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/ysights/badge/?version=latest)](https://ysights.readthedocs.io/en/latest/?badge=latest)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Python library for analyzing data from YSocial simulations. ySights provides comprehensive tools for extracting insights from social media simulation data, including agent behaviors, content dynamics, network structures, and recommendation system effects.

## Features

- **📊 Data Models**: Comprehensive classes for agents, posts, and simulation data
- **🔍 Network Analysis**: Social network extraction and analysis capabilities  
- **🧮 Algorithms**: Profile similarity, paradox detection, and recommendation metrics
- **📈 Visualization**: Rich visualization functions using matplotlib and plotly
- **📚 Documentation**: Complete Sphinx documentation with examples
- **🔄 CI/CD**: Automated testing, formatting, and package distribution

## Installation

### From PyPI (recommended)

```bash
pip install ysights
```

### With PostgreSQL Support

If you want to use PostgreSQL databases instead of SQLite:

```bash
pip install ysights[postgresql]
```

### From Source

```bash
git clone https://github.com/YSocialTwin/ysights.git
cd ysights
pip install -e .
# Or with PostgreSQL support:
pip install -e .[postgresql]
```

### Using Conda

```bash
conda install -c conda-forge ysights
```

## Quick Start

### Using SQLite (default)

```python
from ysights import YDataHandler

# Initialize data handler with your SQLite simulation database
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

# Get posts by a specific agent
agent_id = 1
posts = ydh.posts_by_agent(agent_id)
print(f"Agent {agent_id} created {len(posts.get_posts())} posts")
```

### Using PostgreSQL

```python
from ysights import YDataHandler

# Initialize data handler with PostgreSQL connection string
ydh = YDataHandler('postgresql://user:password@localhost:5432/ysocial_db')

# Use the same API - all methods work identically
agents = ydh.agents()
network = ydh.social_network()
```

**Note**: ySights supports both SQLite and PostgreSQL databases with the same table structure. The API is identical regardless of which database you use.

## Main Components

### 1. Data Models (`ysights.models`)

- **YDataHandler**: Main interface for database operations (supports both SQLite and PostgreSQL)
- **Agents/Agent**: Classes for representing individual agents and agent collections
- **Posts/Post**: Classes for representing posts and post collections

```python
from ysights import YDataHandler

# Works with both SQLite and PostgreSQL
ydh = YDataHandler('simulation.db')  # SQLite
# ydh = YDataHandler('postgresql://user:pass@host/db')  # PostgreSQL

# Get agents by feature
young_agents = ydh.agents_by_feature('age', 25)

# Get agent interest profile
profile = ydh.agent_interest_profile(agent_id=1)
```

### 2. Algorithms (`ysights.algorithms`)

#### Profile Analysis
```python
from ysights.algorithms import profile_topics_similarity

# Calculate profile similarity across the network
similarity = profile_topics_similarity(ydh, network)
```

#### Recommendation Metrics
```python
from ysights.algorithms import engagement_momentum, personalization_balance_score

# Analyze engagement momentum
momentum = engagement_momentum(ydh, time_window_rounds=24)

# Calculate personalization balance
balance = personalization_balance_score(ydh)
```

#### Topic Analysis
```python
from ysights.algorithms import topic_spread, adoption_rate, peak_engagement_time

# Analyze topic dynamics
spread = topic_spread(ydh, topic_id=5)
adoption = adoption_rate(ydh, topic_id=5)
peak_time = peak_engagement_time(ydh, topic_id=5)
```

### 3. Visualization (`ysights.viz`)

#### Global Trends
```python
from ysights.viz import (
    daily_contents_trends,
    trending_hashtags,
    trending_emotions
)

# Visualize daily content trends
fig = daily_contents_trends(ydh)
fig.show()

# Show top trending hashtags
fig = trending_hashtags(ydh, top_n=10)
fig.show()
```

#### Topic Visualizations
```python
from ysights.viz import topic_density_temporal_evolution

# Visualize topic evolution over time
fig = topic_density_temporal_evolution(ydh, min_days=15)
fig.show()
```

#### Profile Analysis
```python
from ysights.viz import (
    profile_similarity_distribution,
    profile_similarity_vs_degree
)

# Visualize profile similarity
fig = profile_similarity_distribution([similarity], ['All Users'])
fig.show()
```

## Documentation

Comprehensive documentation is available at [ysights.readthedocs.io](https://ysights.readthedocs.io/)

### Building Documentation Locally

```bash
cd docs
pip install -r requirements.txt
make html
```

The generated HTML documentation will be in `docs/build/html/`.

## Development

### Setting Up Development Environment

```bash
git clone https://github.com/YSocialTwin/ysights.git
cd ysights
pip install -r requirements.txt
pip install -e .
```

### Code Formatting

This project uses Black for code formatting and isort for import sorting:

```bash
# Install formatting tools
pip install black isort flake8

# Format code
black ysights/
isort ysights/

# Check formatting
black --check ysights/
isort --check-only ysights/
flake8 ysights/
```

### Running Tests

```bash
# Install test dependencies
pip install pytest

# Run tests
pytest ysights/test/
```

Note: Some tests require simulation database files and will be skipped if not available.

## CI/CD

The project includes comprehensive GitHub Actions workflows:

- **CI Workflow**: Automatic code quality checks on every push
  - Black formatting validation
  - isort import sorting validation
  - flake8 linting
  - pytest tests (Python 3.9-3.12)
  
- **Auto-format Workflow**: Automatically formats code on push
  - Runs Black and isort
  - Auto-commits formatting changes

- **Documentation Workflow**: Build and publish Sphinx documentation
  - Automatic build on every push (verifies docs build successfully)
  - Publishes to GitHub Pages on push to main
  - Manual trigger option for on-demand publishing
  - Documentation available at: `https://ysocialtwin.github.io/ysights/`

- **PyPI Publishing**: Build and publish packages to PyPI
  - Manual trigger for Test PyPI
  - Automatic publishing on releases

- **Conda Publishing**: Build and publish conda packages
  - Multi-platform support (Linux, macOS, Windows)
  - Manual trigger with publish option

## Requirements

### Core Dependencies

- Python >= 3.9
- networkx
- matplotlib
- numpy
- scipy
- seaborn
- plotly
- scikit-learn
- pandas
- tqdm

### Optional Dependencies

- **psycopg2-binary** (for PostgreSQL support): Install with `pip install ysights[postgresql]`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please ensure your code:
- Follows Black code style
- Has properly sorted imports (isort)
- Includes docstrings for new functions/classes
- Passes all tests

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Citation

If you use ySights in your research, please cite:

```bibtex
@software{ysights,
  author = {Rossetti, Giulio},
  title = {ySights: A Python library for analyzing YSocial simulation data},
  year = {2024},
  url = {https://github.com/YSocialTwin/ysights}
}
```

## Related Projects

- **YSocial**: The social media simulation framework that generates data analyzed by ySights

## Contact

- **Author**: Giulio Rossetti
- **Email**: giulio.rossetti@gmail.com
- **GitHub**: [@GiulioRossetti](https://github.com/GiulioRossetti)

## Acknowledgments

This project is part of the YSocialTwin ecosystem for social media simulation and analysis.
