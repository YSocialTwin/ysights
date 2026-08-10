"""
Example: Visibility Paradox Statistical Significance per Degree Class
======================================================================

This example demonstrates how to compute and visualize the statistical 
significance of the visibility paradox for different degree classes of nodes.

The analysis bins nodes by their degree (number of connections) and computes:
1. Average paradox score per degree class
2. Statistical significance (p-values) per degree class using null models

This helps identify whether certain types of nodes (by connectivity) 
experience the visibility paradox more strongly than others.
"""

from ysights import YDataHandler
from ysights.algorithms import visibility_paradox_per_degree_class
from ysights.viz import paradox_significance_per_degree_class

# Initialize data handler with your YSocial simulation database
ydh = YDataHandler('/Users/rossetti/PycharmProjects/visibility_paradox/data/old_data/BA_FP.db')
network = ydh.social_network()

print("Computing visibility paradox per degree class...")
print("This may take a few minutes depending on network size and N...")

# Example 1: Using default linear binning
# ----------------------------------------
# This creates 10 equally-spaced bins across the degree range
results = visibility_paradox_per_degree_class(
    ydh, 
    network, 
    N=100,  # Number of null models for statistical testing
    num_bins=20  # Number of degree bins
)

# Display results
print("\nResults with default linear binning:")
print(f"Bin centers: {results['bin_centers']}")
print(f"Paradox scores: {results['paradox_scores']}")
print(f"P-values: {results['p_values']}")
print(f"Nodes per bin: {results['bin_counts']}")

# Create and display visualization
fig = paradox_significance_per_degree_class(results)
fig.savefig('paradox_per_degree_linear.png', dpi=150, bbox_inches='tight')
print("\nVisualization saved to 'paradox_per_degree_linear.png'")


# Example 2: Using custom bin edges
# ----------------------------------
# You can specify custom bins to focus on specific degree ranges
# or to use logarithmic binning for scale-free networks
custom_bins = [0, 5, 10, 20, 50, 100, 200]
results_custom = visibility_paradox_per_degree_class(
    ydh,
    network,
    N=100,
    bins=custom_bins  # Custom bin edges
)

print("\n\nResults with custom bins:")
print(f"Bin edges: {results_custom['bin_edges']}")
print(f"Bin centers: {results_custom['bin_centers']}")
print(f"Paradox scores: {results_custom['paradox_scores']}")
print(f"Nodes per bin: {results_custom['bin_counts']}")

# Create visualization for custom bins
fig_custom = paradox_significance_per_degree_class(results_custom)
fig_custom.savefig('paradox_per_degree_custom.png', dpi=150, bbox_inches='tight')
print("\nCustom binning visualization saved to 'paradox_per_degree_custom.png'")


# Interpretation Guide
# --------------------
print("\n" + "="*70)
print("INTERPRETATION GUIDE")
print("="*70)
print("""
1. P-values (red line, left y-axis):
   - Shows statistical significance for each degree class
   - Values below 0.05 indicate significant paradox effect
   - Lower p-values = stronger statistical evidence
   
2. Paradox Score (blue line, right y-axis):
   - Average paradox score for nodes in that degree class
   - Positive values: nodes see more content from neighbors than 
     neighbors see from them
   - Negative values: opposite effect
   
3. Shaded regions:
   - Red region (p > 0.05): Not statistically significant
   - Orange region (0.01 < p < 0.05): Marginally significant
   - Yellow region (0.001 < p < 0.01): Significant
   - Green region (p < 0.001): Highly significant

4. What to look for:
   - Do high-degree nodes experience the paradox differently than 
     low-degree nodes?
   - At which degree classes is the paradox statistically significant?
   - Are there degree classes with negative paradox scores 
     (inverse effect)?
""")
