#!/bin/bash
# PulseX quick-start script
set -e
cd "$(dirname "$0")"

export PULSEX_FAST="${PULSEX_FAST:-1}"

if [ ! -f data/tweets_cache.jsonl ]; then
  echo "Importing sample tweets..."
  python3 cli.py import-tweets data/sample_tweets.csv
fi

echo "Running full PulseX pipeline..."
python3 cli.py run "$@"
