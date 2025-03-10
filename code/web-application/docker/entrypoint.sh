#!/bin/bash
set -e

# Parse arguments
CODE_FILE=$1
LANGUAGE=$2
TEST_DATA=$3
OUTPUT_FILE=$4
TIMEOUT=${5:-10}  # Default timeout of 10 seconds

echo "Starting evaluation with language: $LANGUAGE"

# Create output directory if it doesn't exist
mkdir -p $(dirname $OUTPUT_FILE)

# Run the appropriate evaluator based on language
case "$LANGUAGE" in
    "python")
        timeout $TIMEOUT python3 /evaluators/python_evaluator.py "$CODE_FILE" "$TEST_DATA" > "$OUTPUT_FILE" 2>&1
        ;;
    "javascript")
        timeout $TIMEOUT node /evaluators/js_evaluator.js "$CODE_FILE" "$TEST_DATA" > "$OUTPUT_FILE" 2>&1
        ;;
    "sql")
        # Start PostgreSQL
        sudo service postgresql start
        timeout $TIMEOUT python3 /evaluators/sql_evaluator.py "$CODE_FILE" "$TEST_DATA" > "$OUTPUT_FILE" 2>&1
        ;;
    *)
        echo '{"status": "error", "message": "Unsupported language"}' > "$OUTPUT_FILE"
        exit 1
        ;;
esac

# Check exit code
EXIT_CODE=$?

# If timeout occurred
if [ $EXIT_CODE -eq 124 ]; then
    echo '{"status": "timeout", "message": "Evaluation timed out"}' > "$OUTPUT_FILE"
    exit 0
fi

# If output file is empty (error occurred but no output)
if [ ! -s "$OUTPUT_FILE" ]; then
    echo '{"status": "error", "message": "Evaluation failed with no output"}' > "$OUTPUT_FILE"
fi

exit 0