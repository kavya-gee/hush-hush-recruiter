#!/usr/bin/env python3
import json
import sys
import traceback
import psycopg2
import re
import time
from typing import Dict, List, Any, Tuple


def load_test_data(test_data_file: str) -> Dict[str, Any]:
    """Load test data from a JSON file."""
    with open(test_data_file, 'r') as f:
        return json.load(f)


def load_submission(code_file: str) -> str:
    """Load SQL submission from file."""
    with open(code_file, 'r') as f:
        return f.read()


def setup_database(connection, schema_file: str) -> None:
    """Set up the database with the schema and test data."""
    with open(schema_file, 'r') as f:
        schema_sql = f.read()

    with connection.cursor() as cursor:
        cursor.execute(schema_sql)
    connection.commit()


def execute_query(connection, query: str) -> List[Dict[str, Any]]:
    """Execute a SQL query and return results as a list of dicts."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)

            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Fetch all rows
            rows = cursor.fetchall() if cursor.description else []

            # Convert rows to list of dictionaries
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))

            return results
    except Exception as e:
        raise Exception(f"Error executing query: {str(e)}")


def run_tests(connection, submission: str, test_data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], float]:
    """
    Run test cases against the submitted SQL code.
    Returns: (success, test_results, score)
    """
    test_cases = test_data.get('test_cases', [])

    # Extract CREATE TABLE statements to ignore during testing
    create_table_statements = re.finditer(r"CREATE\s+TABLE.*?;", submission, re.DOTALL | re.IGNORECASE)
    schema_queries = [stmt.group(0) for stmt in create_table_statements]

    # Setup schema first
    for query in schema_queries:
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
            connection.commit()
        except Exception as e:
            # Return immediately if schema setup fails
            return False, [{
                'test_case': 'schema_setup',
                'passed': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }], 0

    # Extract test queries - queries that don't create tables
    test_queries = []
    for query in re.split(r";", submission):
        query = query.strip()
        if query and not re.match(r"^\s*CREATE\s+TABLE", query, re.IGNORECASE):
            test_queries.append(query + ";")

    passed_tests = 0
    total_tests = len(test_cases)
    test_results = []

    for i, test_case in enumerate(test_cases):
        test_query = test_case.get('query', '')
        expected_result = test_case.get('expected_result', [])

        # If no specific test query provided, use the extracted ones
        if not test_query and i < len(test_queries):
            test_query = test_queries[i]

        if not test_query:
            test_results.append({
                'test_case': i + 1,
                'passed': False,
                'error': 'No query found for this test case',
            })
            continue

        try:
            # Execute the query
            actual_result = execute_query(connection, test_query)

            # Compare results
            # Simplifying comparison by converting to strings
            expected_json = json.dumps(expected_result, sort_keys=True)
            actual_json = json.dumps(actual_result, sort_keys=True)

            result_matches = expected_json == actual_json

            if result_matches:
                passed_tests += 1

            test_results.append({
                'test_case': i + 1,
                'passed': result_matches,
                'query': test_query,
                'expected_result': expected_result,
                'actual_result': actual_result
            })

        except Exception as e:
            test_results.append({
                'test_case': i + 1,
                'passed': False,
                'query': test_query,
                'expected_result': expected_result,
                'error': str(e),
                'traceback': traceback.format_exc()
            })

    score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    return passed_tests == total_tests, test_results, score


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            'status': 'error',
            'message': 'Insufficient arguments. Usage: sql_evaluator.py <code_file> <test_data_file>'
        }))
        sys.exit(1)

    code_file = sys.argv[1]
    test_data_file = sys.argv[2]

    try:
        test_data = load_test_data(test_data_file)
        submission = load_submission(code_file)

        # Connect to the database
        connection = psycopg2.connect(
            dbname="evaluation_db",
            user="evaluator",
            password="secure_password",
            host="localhost"
        )

        # Setup database if a schema file is provided
        schema_file = test_data.get('schema_file')
        if schema_file:
            setup_database(connection, schema_file)

        success, test_results, score = run_tests(connection, submission, test_data)

        print(json.dumps({
            'status': 'success',
            'passed_all': success,
            'evaluation_score': score,
            'test_results': test_results
        }))

        # Close the connection
        connection.close()

    except Exception as e:
        print(json.dumps({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()