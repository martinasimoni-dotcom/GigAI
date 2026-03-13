#!/usr/bin/env bash
# infra/pubsub/setup.sh
# One-time GCP Pub/Sub topic and subscription setup for GigAI.
# Run this once per GCP project before starting the pipeline.
#
# Usage: GOOGLE_CLOUD_PROJECT=my-project bash infra/pubsub/setup.sh

set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:?GOOGLE_CLOUD_PROJECT env var is required}"

echo "Setting up Pub/Sub topics for project: $PROJECT"

# Create topics (idempotent — gcloud returns 0 if already exists with --quiet)
for TOPIC in raw-events normalized-events enriched-events signals; do
  echo "Creating topic: $TOPIC"
  gcloud pubsub topics create "$TOPIC" \
    --project="$PROJECT" \
    --quiet 2>/dev/null || echo "  (topic $TOPIC already exists, skipping)"
done

# Create pull subscription for raw-events (used by data processing in Phase 3)
echo "Creating subscription: raw-events-sub"
gcloud pubsub subscriptions create raw-events-sub \
  --topic=raw-events \
  --project="$PROJECT" \
  --ack-deadline=60 \
  --quiet 2>/dev/null || echo "  (subscription raw-events-sub already exists, skipping)"

echo "Pub/Sub setup complete."
echo "Topics: raw-events, normalized-events, enriched-events, signals"
echo "Subscriptions: raw-events-sub"
