# Prediction Whale DB — Domain Glossary

Use these terms consistently in code, docs, and plans. Add new nouns here before they spread across the repo.

## Market

A single prediction market from Polymarket or Kalshi. Markets are the primary unit of selection, matching, collection, and analysis.

## Trade

An individual executed trade event in a market. Trades are the base record collected by the batch pipeline and the streaming feed.

## Historical slice

The bounded set of markets and trades selected for the offline collection phase. This is the researched training set, not the full platform history.

## Active market

A currently live market with enough volume to matter for the streaming alert feed. Active markets are refreshed periodically, not fixed forever.

## Batch collection

The offline ingestion path that re-collects historical trades and persists raw responses before normalization.

## Streaming feed

The live path that follows currently active markets and emits new trade events or alerts as they arrive.

## Bronze layer

Raw collected data stored with minimal transformation. Bronze is the audit trail for what the API returned.

## Silver layer

Normalized, typed, deduplicated trade data produced from Bronze.

## Gold layer

Derived features, scores, alerts, and downstream aggregates used by the API or dashboard.

## Match candidate

A proposed cross-platform pair between a Polymarket market and a Kalshi market. Candidates are scored before manual review.

## Confirmed match

A match candidate that survived human review and is accepted as a real cross-platform pair.

## Alert

A scored event or condition that should surface to the user from the live pipeline.

## Integrity score

A derived score used to rank suspicious or noteworthy markets, trades, or patterns.
