# Remaining Microblog / Forum Work

This checklist captures what is still missing from `MICROBLOG_FORUM_EXTENSIONS.md`,
ordered by implementation priority.

## 1. Remove the last explicit stub

- [x] Implement `sentiment_diffusion_metrics` in `ysights/algorithms/recommenders.py`.
- [x] Add regression coverage for the new behavior.
- [x] Update docs so the function is no longer presented as a placeholder.

## 2. Add exposure and feedback-loop analytics

- [x] Model recommendation exposure as a first-class analytic.
- [x] Add exposure-to-action conversion metrics.
- [x] Add recommendation acceptance metrics.
- [x] Add reply and mention conversion metrics.
- [x] Add feedback-loop metrics for reinforcement and recirculation.

## 3. Expand semantic content enrichment

- [x] Add text normalization helpers for URLs, hashtags, mentions, punctuation, and casing.
- [x] Add readability-oriented features.
- [x] Add lexical diversity and punctuation-intensity metrics.
- [x] Add optional embedding-based similarity helpers.

## 4. Deepen multiplex interaction analysis

- Add layer-specific centrality metrics.
- Add interaction tie-strength analysis by layer.
- Add richer overlap reporting between layers.
- Add polarization / reciprocity views over combined interaction graphs.

## 5. Harden performance for larger runs

- Add query batching for repeated analytics.
- Add lazy loading for expensive derived objects.
- Expand graph-construction optimizations.
- Keep benchmark and cache coverage in sync with new code paths.

## 6. Finish documentation alignment

- Keep tutorials and notebooks aligned with the implemented API surface.
- Remove any remaining placeholder language from public docs.
- Ensure new methods are documented with opaque identifiers, not numeric-only examples.

## Suggested Order of Work

1. Implement `sentiment_diffusion_metrics`.
2. Add exposure / feedback analytics.
3. Add semantic enrichment helpers.
4. Expand multiplex metrics.
5. Improve performance and scale handling.
6. Refresh docs after each phase.
