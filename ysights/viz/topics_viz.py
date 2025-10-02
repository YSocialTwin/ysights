"""
Topic Visualization Functions
==============================

This module provides visualization functions for analyzing topic dynamics
and evolution in YSocial simulations. It focuses on temporal patterns of
interest and topic density across different user groups.

Functions:
    - topic_density_temporal_evolution: Visualize topic density over time as a heatmap

Example:
    Visualizing topic evolution::

        from ysights import YDataHandler
        from ysights.viz import topic_density_temporal_evolution

        ydh = YDataHandler('path/to/database.db')

        # Visualize all topics over time
        fig = topic_density_temporal_evolution(ydh, min_days=15)
        fig.show()

        # Filter by user leaning
        fig_left = topic_density_temporal_evolution(ydh, min_days=10, leaning='left')
        fig_left.update_layout(title="Topics: Left-leaning Users")
        fig_left.show()

See Also:
    - :mod:`ysights.algorithms.topics`: Topic analysis algorithms
    - :mod:`ysights.viz.global_trends`: Aggregate trend visualizations
"""

import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.preprocessing import MinMaxScaler

from ysights.models.YDataHandler import YDataHandler


def topic_density_temporal_evolution(
    YDH: YDataHandler, min_days=15, leaning: str = None
):
    """
    Visualize the temporal evolution of topic density in a heatmap format.
    This function retrieves user interest data, aggregates it by interest and day, and generates a heatmap

    :param YDH: YDataHandler instance for database operations
    :param min_days: Minimum number of days an interest must be present to be included in the heatmap
    :param leaning: Optional parameter to filter interests by user leaning (e.g., 'democrats', 'republican', etc.)
    :return: A Plotly heatmap figure showing the density of topics over time
    """

    query = """
        SELECT ui.interest_id, i.interest, r.day, count(ui.id)
        FROM user_interest as ui, rounds as r, interests as i, user_mgmt as u
        WHERE ui.round_id = r.id and i.iid = ui.interest_id and ui.user_id == u.id"""

    if leaning is not None:
        query = query + f" and  u.leaning == '{leaning}' "

    query = query + " GROUP BY ui.interest_id, r.day"

    rows = YDH.custom_query(query)

    # Initialize scaler
    scaler = MinMaxScaler()

    # Create custom colorscale with white for zero
    colorscale = [
        [0, "white"],
        [1, "red"],
    ]  # White for 0, light blue for values above 0

    df = pd.DataFrame(rows, columns=["id", "interest", "day", "count"])

    df = df[df["day"] > 0]

    # Pivot table (interest as index)
    heatmap_df = df.pivot(index="interest", columns="day", values="count").fillna(0)

    # Convert to NumPy array
    heatmap_data = heatmap_df.to_numpy()
    # heatmap_data = np.array([scaler.fit_transform(row.reshape(-1, 1)).flatten() for row in heatmap_data])
    original_interest_labels = heatmap_df.index.to_numpy()

    nonzero_count = np.count_nonzero(heatmap_data, axis=1)

    valid_rows = nonzero_count >= min_days
    filtered_heatmap_data = heatmap_data[valid_rows]
    filtered_interest_labels = original_interest_labels[valid_rows]

    # Find the first nonzero column index in each remaining row
    first_nonzero_index = np.apply_along_axis(
        lambda row: np.argmax(row != 0) if np.any(row != 0) else np.inf,
        axis=1,
        arr=filtered_heatmap_data,
    )

    # Count nonzero elements again (after filtering)
    filtered_nonzero_count = nonzero_count[valid_rows]

    # Sorting order:
    # - Primary: First nonzero column index (ascending) → Start earlier first
    # - Secondary: Number of nonzero elements (descending) → Longer periods first
    sorted_indices = np.lexsort(
        (-filtered_nonzero_count, first_nonzero_index)
    )  # << FIXED ORDER

    # Reorder heatmap data and interest labels
    sorted_heatmap_data = filtered_heatmap_data[sorted_indices]
    sorted_interest_labels = filtered_interest_labels[sorted_indices]

    # Generate heatmap with reordered data
    fig = px.imshow(
        sorted_heatmap_data,
        labels=dict(x="Day", y="Interest"),
        x=sorted(df["day"].unique()),  # Days sorted as before
        y=sorted_interest_labels,  # Interest labels reordered
        color_continuous_scale=colorscale,
        aspect="auto",
    )

    # Set title and other properties
    fig.update_layout(
        title="Topics Density Temporal Evolution",
        xaxis_title="Day",
        yaxis_title="",
        xaxis=dict(
            tickmode="array", tickvals=list(df["day"].unique())[::5]
        ),  # Show every 5th day on x-axis
        yaxis=dict(
            tickmode="array", tickvals=list(df["interest"].unique())[::1]
        ),  # Show every 10th ID on y-axis
        coloraxis_showscale=True,
        height=1500,  # Increase height to make space for rows (adjust based on the number of rows)
        width=1000,  # Show the color scale
    )

    # Show interactive plot
    return fig
