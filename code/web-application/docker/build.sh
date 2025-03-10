#!/bin/bash
set -e

# Script to build the Docker image for code evaluation

echo "Building Docker image for code evaluation..."

# Navigate to the docker directory
cd "$(dirname "$0")"

# Build the Docker image
docker build -t recruiter-code-evaluator:latest .

echo "Docker image built successfully!"
echo "You can now use the image for code evaluation."