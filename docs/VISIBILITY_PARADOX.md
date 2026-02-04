# Visibility Paradox: Mathematical Formulation and Implementation

## Table of Contents
1. [Introduction](#introduction)
2. [Conceptual Definition](#conceptual-definition)
3. [Mathematical Formulation](#mathematical-formulation)
   - [Local Level (Node-Level Paradox)](#local-level-node-level-paradox)
   - [Global Level (Network-Wide Paradox)](#global-level-network-wide-paradox)
4. [Assumptions](#assumptions)
5. [Implementation Details](#implementation-details)
6. [Null Model for Statistical Testing](#null-model-for-statistical-testing)
7. [Significance Testing](#significance-testing)
8. [Extensions and Variations](#extensions-and-variations)
9. [References](#references)

---

## Introduction

The **Visibility Paradox** is a phenomenon observed in social networks where content created by users receives asymmetric visibility compared to content they see from their neighbors. This paradox is analogous to the friendship paradox (Feld, 1991) but applied to content visibility and recommendations in social media contexts.

The paradox manifests when most users perceive that their content receives less visibility from their neighbors than the content they see from those same neighbors, even though the aggregate statistics might suggest balance or symmetry.

---

## Conceptual Definition

The visibility paradox occurs when there is a systematic imbalance between:

1. **Inbound Visibility**: How much content from a user's neighbors appears in their feed (content they are recommended to see)
2. **Outbound Visibility**: How much of a user's content appears in their neighbors' feeds (content that is recommended to others)

A user experiences the paradox when they see more content from their neighbors than their neighbors see from them, creating a perception of under-representation.

---

## Mathematical Formulation

### Local Level (Node-Level Paradox)

For a given node (user) $n$ in a social network graph $G = (V, E)$, we define the **local paradox coefficient** $\delta_n$ as follows:

#### Notation:
- $G = (V, E)$: Social network graph with vertices $V$ (users) and edges $E$ (connections)
- $N(n)$: Set of neighbors of node $n$, i.e., $N(n) = \{v \in V : (n,v) \in E\}$
- $k_n = |N(n)|$: Degree of node $n$ (number of neighbors)
- $P(u)$: Set of posts created by user $u$
- $R(u)$: Set of posts recommended to user $u$ (posts appearing in their feed)

#### Per-Neighbor Visibility Score:

For each neighbor $v \in N(n)$, we compute a pairwise visibility score $s_{n,v}$:

$$s_{n,v} = |P(v) \cap R(n)| - |P(n) \cap R(v)|$$

Where:
- $|P(v) \cap R(n)|$ = number of posts created by neighbor $v$ that are recommended to user $n$
- $|P(n) \cap R(v)|$ = number of posts created by user $n$ that are recommended to neighbor $v$

**Interpretation**: 
- $s_{n,v} > 0$: User $n$ sees more content from $v$ than $v$ sees from $n$
- $s_{n,v} < 0$: User $n$ sees less content from $v$ than $v$ sees from $n$
- $s_{n,v} = 0$: Symmetric visibility between $n$ and $v$

#### Node-Level Paradox Coefficient:

The local paradox coefficient for node $n$ is the average of these pairwise scores:

$$\delta_n = \frac{1}{k_n} \sum_{v \in N(n)} s_{n,v} = \frac{1}{k_n} \sum_{v \in N(n)} \left( |P(v) \cap R(n)| - |P(n) \cap R(v)| \right)$$

**Properties**:
- $\delta_n > 0$: User $n$ experiences the visibility paradox (sees more than they are seen)
- $\delta_n < 0$: User $n$ experiences an inverse paradox (is seen more than they see)
- $\delta_n = 0$: Perfect visibility balance for user $n$

**Implementation Reference** (from `__stats()` function):
```python
for n in g.nodes():
    if n in users_to_impressions_total:
        read = {pid: None for pid in set(user_to_posts_read[n])}
        scores = []
        for v in g.neighbors(n):
            # Count posts from neighbor v that appear in n's recommendations
            p_tot = 0
            if v in user_to_posts:
                for post in user_to_posts[v]:
                    if post in read:
                        p_tot += 1
            
            # Count posts from n that appear in v's recommendations
            v_tot = 0
            v_read = {pid: None for pid in set(user_to_posts_read[v])}
            if n in user_to_posts:
                for post in user_to_posts[n]:
                    if post in v_read:
                        v_tot += 1
            
            # Compute pairwise score
            scores.append(p_tot - v_tot)
        
        # Average over all neighbors
        delta.append((1 / nx.degree(g, n)) * sum(scores))
```

### Global Level (Network-Wide Paradox)

The **global paradox score** $\Delta$ is the mean of all individual node coefficients:

$$\Delta = \frac{1}{|V'|} \sum_{n \in V'} \delta_n$$

Where $V' \subseteq V$ is the set of nodes for which we can compute the paradox coefficient (nodes with posts and/or recommendations).

**Expanded Form**:

$$\Delta = \frac{1}{|V'|} \sum_{n \in V'} \left[ \frac{1}{k_n} \sum_{v \in N(n)} \left( |P(v) \cap R(n)| - |P(n) \cap R(v)| \right) \right]$$

**Interpretation**:
- $\Delta > 0$: Network-wide visibility paradox exists (average user sees more than they are seen)
- $\Delta = 0$: Network exhibits perfect visibility balance on average
- $\Delta < 0$: Network exhibits inverse paradox (not typical in real systems)

**Statistical Significance**: The global paradox score $\Delta$ is tested against a null hypothesis that the observed value is not different from what would be expected by chance (see [Null Model](#null-model-for-statistical-testing)).

---

## Assumptions

The visibility paradox formulation relies on several key assumptions:

### 1. **Graph Structure Assumption**
- The social network is represented as an undirected graph $G = (V, E)$
- Edges represent bidirectional social connections (friendships, follows)
- The graph is static during the analysis period (or analyzed at discrete snapshots)

### 2. **Content Attribution Assumption**
- Each post $p$ has a unique creator: $\exists! u \in V : p \in P(u)$
- Posts are correctly attributed to their creators
- The mapping $P: V \to 2^{\text{Posts}}$ is well-defined

### 3. **Recommendation Data Completeness**
- Recommendation data $R(u)$ captures all posts shown to user $u$ during the analysis period
- The recommendation mechanism is consistent across users (though not necessarily uniform)
- We have access to the complete recommendation logs

### 4. **Independence Assumption for Null Model**
- Under the null hypothesis, post authorship is independent of content visibility
- Post creation counts per user are fixed (preserved in null models)
- The recommendation mechanism itself is preserved (only authorship is permuted)

### 5. **Temporal Considerations**
- Analysis is performed over a fixed time window
- We assume quasi-stationarity: network structure and user behavior are relatively stable
- Temporal dynamics are aggregated (cumulative counts)

### 6. **Degree Normalization**
- The $1/k_n$ normalization assumes that each neighbor contributes equally to the local paradox
- This choice makes coefficients comparable across nodes with different degrees
- Alternative normalizations (e.g., by total posts or impressions) are possible

---

## Implementation Details

### Data Structures

The implementation uses the following key data structures:

1. **`user_to_posts`**: Dict mapping user IDs to lists of post IDs they created
   - Type: `Dict[UserId, List[PostId]]`
   - Example: `{user_1: [post_1, post_2, post_3], user_2: [post_4], ...}`

2. **`user_to_posts_read`**: Dict mapping user IDs to lists of post IDs recommended to them
   - Type: `Dict[UserId, List[PostId]]`
   - Example: `{user_1: [post_4, post_7], user_2: [post_1, post_3], ...}`

3. **`post_recs`**: Dict mapping post IDs to their total impression counts
   - Type: `Dict[PostId, int]`
   - Used for visibility metrics but not directly in paradox computation

4. **`g`**: NetworkX graph object representing the social network
   - Nodes: User IDs
   - Edges: Social connections

### Algorithm Steps

**Step 1: Data Extraction**
```python
post_recs, user_to_posts_read = YDH.recommendations_per_post_per_user()
posts = YDH.posts()
```

**Step 2: Build Post-to-User Mappings**
```python
user_to_posts = {}  # user -> [posts]
post_to_users = {}  # post -> user
for post in posts.get_posts():
    user_to_posts[post.user_id].append(post.id)
    post_to_users[post.id] = post.user_id
```

**Step 3: Compute Node-Level Coefficients**
```python
nodes_coeffs = __stats(users_to_impressions_total, 
                       user_to_posts_read, 
                       user_to_posts, 
                       g)
```

**Step 4: Compute Global Score**
```python
paradox_score = np.mean(nodes_coeffs)
```

**Step 5: Statistical Testing** (if N > 0)
```python
# Generate null models
null_models = __generate_randomized_mappings(user_to_posts, N, x=1)

# Compute null distribution
null_means_dist = []
for null_model in null_models:
    null_score = np.mean(__stats(..., null_model, ...))
    null_means_dist.append(null_score)

# Perform z-test
z_score, p_value = __z_test(observed_mean, null_means_dist)
```

---

## Null Model for Statistical Testing

To determine whether an observed paradox score $\Delta_{\text{obs}}$ is statistically significant, we compare it against a **null model** that represents the expected distribution under the null hypothesis.

### Null Hypothesis

**$H_0$**: The observed visibility paradox is not different from what would be expected if post authorship were random, given the fixed network structure and recommendation patterns.

Formally: Post creation is independent of the visibility patterns in the network.

### Null Model Construction

The null model is constructed using a **configuration model** approach that preserves key structural properties:

#### Preserved Properties:
1. **Network structure**: Graph $G = (V, E)$ remains unchanged
2. **Post production per user**: $|P(u)|$ is fixed for all $u \in V$
3. **Recommendation patterns**: $R(u)$ remains unchanged for all $u \in V$
4. **Total number of posts**: $\sum_{u \in V} |P(u)|$ is constant

#### Randomized Property:
- **Post authorship**: The assignment of posts to users is randomized while preserving post counts

### Randomization Procedure

For each null model realization $i = 1, 2, \ldots, N$:

**Step 1: Extract Posts**
- Collect all posts from all users: $\mathcal{P} = \bigcup_{u \in V} P(u)$

**Step 2: Shuffle Posts**
- Randomly permute the post IDs: $\mathcal{P}' = \text{shuffle}(\mathcal{P})$

**Step 3: Reassign Posts**
- For each user $u$ in arbitrary order:
  - Count original posts: $n_u = |P(u)|$
  - Assign next $n_u$ posts from $\mathcal{P}'$ to user $u$: $P'(u) = \{\text{next } n_u \text{ posts from } \mathcal{P}'\}$

**Mathematical Formulation**:

Let $\pi: \mathcal{P} \to \mathcal{P}$ be a random permutation. For each user $u$:

$$P'(u) = \{\pi(p) : p \in P(u)\}$$

More precisely, if we enumerate posts as $\mathcal{P} = \{p_1, p_2, \ldots, p_M\}$ and users produce posts in ranges $[a_u, b_u]$:

$$P'(u) = \{\pi(p_i) : i \in [a_u, b_u]\}$$

**Implementation** (from `__generate_randomized_mappings()`):
```python
# Extract all posts from all users
randomized_posts = [post for user in users 
                    for post in original_dict[user]]

# Shuffle the posts
random.shuffle(randomized_posts)

# Reassign to users preserving counts
shuffled_posts = iter(randomized_posts)
user_to_posts_null = {}
for user in users:
    count = len(original_dict[user])
    user_to_posts_null[user] = [next(shuffled_posts) 
                                 for _ in range(count)]
```

### Null Distribution

After generating $N$ null model realizations, we compute the paradox score for each:

$$\Delta^{(i)}_{\text{null}} = \frac{1}{|V'|} \sum_{n \in V'} \delta_n^{(i)}, \quad i = 1, 2, \ldots, N$$

The **null distribution** is:

$$\mathcal{D}_{\text{null}} = \{\Delta^{(1)}_{\text{null}}, \Delta^{(2)}_{\text{null}}, \ldots, \Delta^{(N)}_{\text{null}}\}$$

This distribution represents the expected variation in paradox scores under the null hypothesis of random post authorship.

---

## Significance Testing

### Z-Test Formulation

We use a **one-sample Z-test** to assess whether the observed paradox score differs significantly from the null distribution.

#### Test Statistic

$$Z = \frac{\Delta_{\text{obs}} - \mu_{\text{null}}}{\sigma_{\text{null}}}$$

Where:
- $\Delta_{\text{obs}}$: Observed global paradox score
- $\mu_{\text{null}} = \frac{1}{N} \sum_{i=1}^{N} \Delta^{(i)}_{\text{null}}$: Mean of null distribution
- $\sigma_{\text{null}} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (\Delta^{(i)}_{\text{null}} - \mu_{\text{null}})^2}$: Standard deviation of null distribution

#### P-Value Calculation

Under the assumption that the null distribution is approximately normal (justified by the Central Limit Theorem for large $N$), the p-value is:

$$p = 2 \cdot P(Z_{\text{standard}} \geq |Z|) = 2 \cdot \Phi(-|Z|)$$

Where $\Phi$ is the cumulative distribution function of the standard normal distribution, and we use a **two-tailed test** because we're interested in deviations in either direction.

**Implementation**:
```python
def __z_test(observed_mean, synthetic_means):
    synthetic_means = np.array(synthetic_means)
    mu = np.mean(synthetic_means)
    sigma = np.std(synthetic_means, ddof=0)  # population std
    
    z_score = (observed_mean - mu) / sigma
    p_value = 2 * norm.sf(abs(z_score))  # two-tailed
    
    return z_score, p_value
```

### Interpretation Guidelines

| p-value | Interpretation |
|---------|----------------|
| $p < 0.001$ | Highly significant: Strong evidence of visibility paradox |
| $0.001 \leq p < 0.01$ | Very significant: Clear evidence of paradox |
| $0.01 \leq p < 0.05$ | Significant: Moderate evidence of paradox |
| $p \geq 0.05$ | Not significant: Insufficient evidence to reject $H_0$ |

**Z-score interpretation**:
- $Z > 0$: Observed paradox is stronger than expected by chance
- $Z < 0$: Observed paradox is weaker than expected (or inverse paradox)
- $|Z| > 2$: Approximately $p < 0.05$ (rule of thumb)
- $|Z| > 3$: Approximately $p < 0.01$ (strong evidence)

---

## Extensions and Variations

### 1. Degree-Stratified Analysis

The visibility paradox can be analyzed separately for different degree classes:

$$\Delta_{\text{bin}} = \frac{1}{|V_{\text{bin}}|} \sum_{n \in V_{\text{bin}}} \delta_n$$

Where $V_{\text{bin}} = \{n \in V : k_{\text{min}} \leq k_n < k_{\text{max}}\}$ is a degree bin.

This allows investigation of whether the paradox affects high-degree (hub) nodes differently from low-degree (peripheral) nodes.

**Implementation**: `visibility_paradox_per_degree_class()` function.

### 2. Weighted Paradox Score

Instead of simple counts, we can weight by impressions:

$$\delta_n^{\text{weighted}} = \frac{1}{k_n} \sum_{v \in N(n)} \left( \sum_{p \in P(v) \cap R(n)} I(p) - \sum_{p \in P(n) \cap R(v)} I(p) \right)$$

Where $I(p)$ is the number of impressions (views) post $p$ received.

### 3. Temporal Dynamics

The paradox can be tracked over time:

$$\Delta(t) = \text{paradox score computed over time window } [t, t+\tau]$$

This reveals how the paradox evolves as the network and user behavior change.

### 4. Partial Population Analysis

Analyze the paradox for a subset of users:

$$\Delta_{x} = \text{paradox score when } x\% \text{ of users are subject to recommendations}$$

**Implementation**: `visibility_paradox_population_size_null()` function.

This helps understand how recommendation system coverage affects the paradox.

---

## References

### Theoretical Background

1. **Feld, S. L. (1991)**. "Why Your Friends Have More Friends Than You Do." *American Journal of Sociology*, 96(6), 1464-1477.
   - Original friendship paradox paper
   - Theoretical foundation for social network paradoxes

2. **Eom, Y. H., & Jo, H. H. (2014)**. "Generalized friendship paradox in complex networks: The case of scientific collaboration." *Scientific Reports*, 4, 4603.
   - Extension of friendship paradox to weighted networks
   - Relevant for understanding visibility as a weighted measure

3. **Hodas, N., Kooti, F., & Lerman, K. (2013)**. "Friendship Paradox Redux: Your Friends Are More Interesting Than You." *ICWSM*.
   - Application to social media and content sharing
   - Direct precursor to visibility paradox concept

### Related Concepts

4. **Attention Inequality**: The distribution of attention in social networks is highly skewed
5. **Filter Bubbles**: Algorithmic curation can create asymmetric information exposure
6. **Echo Chambers**: Network structure combined with algorithmic recommendations can reinforce existing patterns

### Implementation References

- **NetworkX Documentation**: Graph algorithms and analysis
- **SciPy Stats**: Statistical testing functions (`norm.sf` for p-value calculation)
- **NumPy**: Numerical operations and array handling

---

## Appendix: Complete Mathematical Summary

### Node-Level Formulation

$$\delta_n = \frac{1}{k_n} \sum_{v \in N(n)} \left( |P(v) \cap R(n)| - |P(n) \cap R(v)| \right)$$

### Global-Level Formulation

$$\Delta = \frac{1}{|V'|} \sum_{n \in V'} \delta_n$$

### Null Model

$$P'(u) = \text{random reassignment preserving } |P(u)| \text{ for all } u$$

### Significance Test

$$Z = \frac{\Delta_{\text{obs}} - \mu_{\text{null}}}{\sigma_{\text{null}}}, \quad p = 2\Phi(-|Z|)$$

### Decision Rule

Reject $H_0$ (no paradox) if $p < \alpha$ (typically $\alpha = 0.05$)

---

## Usage Example

```python
from ysights import YDataHandler
from ysights.algorithms import visibility_paradox

# Load data
ydh = YDataHandler('simulation_database.db')
network = ydh.social_network()

# Compute paradox with 100 null models
results = visibility_paradox(ydh, network, N=100)

print(f"Global Paradox Score (Δ): {results['paradox_score']:.4f}")
print(f"Z-score: {results['z_score']:.4f}")
print(f"P-value: {results['p_value']:.4f}")

if results['p_value'] < 0.05:
    print("✓ Visibility paradox is statistically significant")
    if results['paradox_score'] > 0:
        print("  → Users see more from neighbors than neighbors see from them")
else:
    print("✗ No significant visibility paradox detected")
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-04  
**Corresponding Code Version**: ysights 0.1.1+
