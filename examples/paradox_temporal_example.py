"""
Example: Temporal Dynamics of the Visibility Paradox
=====================================================

This example demonstrates how to track the visibility paradox over time
with user-defined temporal granularity.

The temporal analysis reveals how the paradox evolves during the simulation,
showing both the paradox score and its statistical significance at regular
time intervals.
"""

from ysights import YDataHandler
from ysights.algorithms import visibility_paradox_temporal
from ysights.viz import paradox_temporal_evolution

# Initialize data handler with your YSocial simulation database
ydh = YDataHandler('path/to/your/database.db')
network = ydh.social_network()

print("Computing temporal evolution of visibility paradox...")
print("This may take several minutes depending on simulation length...")

# Example 1: Track paradox every day
# ----------------------------------------
# This creates time windows of 1 day (24 hours)
print("\n1. Computing paradox evolution with 1-day granularity...")
results_daily = visibility_paradox_temporal(
    ydh, 
    network, 
    temporal_granularity=(1, 0),  # 1 day, 0 hours
    N=50  # Number of null models per time window
)

print(f"   Computed paradox for {len(results_daily['time_points'])} time windows")
print(f"   First window: Day {results_daily['time_points'][0][0]}, Hour {results_daily['time_points'][0][1]}")
print(f"   First paradox score: {results_daily['paradox_scores'][0]:.4f}")

# Create and display visualization
fig = paradox_temporal_evolution(results_daily)
fig.savefig('paradox_temporal_daily.png', dpi=150, bbox_inches='tight')
print("   Visualization saved to 'paradox_temporal_daily.png'")


# Example 2: Track paradox every 12 hours
# ----------------------------------------
# This creates time windows of 12 hours for finer temporal resolution
print("\n2. Computing paradox evolution with 12-hour granularity...")
results_12h = visibility_paradox_temporal(
    ydh,
    network,
    temporal_granularity=(0, 12),  # 0 days, 12 hours
    N=50
)

print(f"   Computed paradox for {len(results_12h['time_points'])} time windows")

# Create and display visualization
fig = paradox_temporal_evolution(results_12h)
fig.savefig('paradox_temporal_12h.png', dpi=150, bbox_inches='tight')
print("   Visualization saved to 'paradox_temporal_12h.png'")


# Example 3: Custom granularity - every 26 hours (1 day + 2 hours)
# ----------------------------------------------------------------
print("\n3. Computing paradox evolution with custom 26-hour granularity...")
results_26h = visibility_paradox_temporal(
    ydh,
    network,
    temporal_granularity=(1, 2),  # 1 day + 2 hours = 26 hours
    N=50
)

print(f"   Computed paradox for {len(results_26h['time_points'])} time windows")

# Create and display visualization
fig = paradox_temporal_evolution(results_26h)
fig.savefig('paradox_temporal_26h.png', dpi=150, bbox_inches='tight')
print("   Visualization saved to 'paradox_temporal_26h.png'")


# Interpretation Guide
# --------------------
print("\n" + "="*70)
print("INTERPRETATION GUIDE")
print("="*70)
print("""
1. P-values (red line, left y-axis):
   - Shows statistical significance at each time point
   - Values below 0.05 indicate significant paradox effect
   - Lower p-values = stronger statistical evidence
   - Log scale helps visualize significance thresholds
   
2. Paradox Score (blue line, right y-axis):
   - Average paradox score for each time window
   - Positive values: users see more content from neighbors than 
     neighbors see from them (paradox present)
   - Negative values: inverse effect
   - Zero line indicates perfect balance
   
3. Shaded regions:
   - Red region (p > 0.05): Not statistically significant
   - Orange region (0.01 < p < 0.05): Marginally significant
   - Yellow region (0.001 < p < 0.01): Significant
   - Green region (p < 0.001): Highly significant

4. Temporal patterns to look for:
   - Does the paradox strengthen or weaken over time?
   - Are there periods where the paradox is not significant?
   - Do we see cyclical patterns (daily/weekly cycles)?
   - When does the paradox first become significant?
   - Are there sudden changes in paradox strength?

5. Time window selection:
   - Smaller windows (e.g., 12h): Better temporal resolution, 
     but more noisy and may have insufficient data per window
   - Larger windows (e.g., 1-2 days): Smoother trends, 
     but less temporal detail
   - Choose based on your research question and data volume

6. Comparing different granularities:
   - Daily view: Good for overall trends
   - 12-hour view: Captures diurnal patterns
   - Custom windows: Can align with specific simulation events
""")

print("\nAnalysis complete! Check the saved PNG files for visualizations.")
