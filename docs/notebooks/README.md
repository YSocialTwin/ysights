# ySights Tutorial Notebooks

This directory contains comprehensive Jupyter notebooks demonstrating ySights functionality.

## Notebooks

### 1. Getting Started (`01_getting_started.ipynb`)
Introduction to ySights basics:
- Initializing YDataHandler
- Loading and exploring simulation data
- Working with Agents and Posts
- Using opaque identifiers from the dataset
- Built-in summaries and cache diagnostics
- Basic data queries and visualizations

### 2. Network Analysis (`02_network_analysis.ipynb`)
Social network extraction and analysis:
- Extracting social and mention networks
- Computing network metrics (density, centrality)
- Analyzing ego networks
- Thread summaries and graph metrics
- Community detection
- Network visualization

### 3. Algorithms (`03_algorithms.ipynb`)
Advanced analytical algorithms:
- Profile similarity analysis
- Semantic text enrichment and similarity checks
- Sentiment diffusion and recommendation exposure analytics
- Visibility paradox detection
- Recommendation system metrics
- Topic lifecycle analysis
- Multiplex interaction diagnostics
- Moderation and forum session summaries

### 4. Visualization (`04_visualization.ipynb`)
Creating publication-ready plots:
- Global trends (daily trends, hashtags, emotions)
- Topic evolution visualizations
- Profile similarity plots
- Semantic, sentiment, and multiplex diagnostics
- Summary and moderation diagnostics
- Recommendation system analysis
- Custom dashboards

## Usage

### Prerequisites
```bash
pip install ysights jupyter matplotlib numpy scipy networkx plotly
```

### Running the Notebooks

1. Start Jupyter:
```bash
jupyter notebook
```

2. Navigate to the `docs/notebooks/` directory

3. Open any notebook and replace `'path/to/your/simulation.db'` with your actual database path

4. Run cells sequentially using Shift+Enter

### Expected Database Structure

These notebooks expect a YSocial simulation database (`.db` file) with tables for:
- Agents (users)
- Posts (content)
- Reactions (likes, etc.)
- Recommendations
- Social network connections

## Learning Path

**Recommended order:**
1. Start with "Getting Started" to understand basics
2. Progress to "Network Analysis" for graph analysis
3. Explore "Algorithms" for advanced metrics, semantic enrichment, and multiplex analytics
4. Master "Visualization" for creating plots

## Tips

- Each notebook is self-contained but builds on concepts from previous ones
- Code cells include detailed comments explaining each step
- All visualizations include interpretive text
- Modify parameters to explore different aspects of your data

## Support

- [ySights Documentation](https://ysights.readthedocs.io/)
- [GitHub Issues](https://github.com/YSocialTwin/ysights/issues)
- Contact: giulio.rossetti@gmail.com
