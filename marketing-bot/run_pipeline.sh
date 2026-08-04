#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Starting Marketing Bot Pipeline..."
python3 scraper.py
python3 llm_summarizer.py
python3 publisher.py
echo "Pipeline completed successfully!"
