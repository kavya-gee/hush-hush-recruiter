#!/usr/bin/env python3
import json
import sys
import traceback
import importlib.util
import time
from typing import Dict, List, Any, Tuple


def load_test_data(test_data_file: str) -> Dict[str, Any]:
    """Load test data from a JSON file."""
    with open(test_data_file, 'r') as f:
        return json.load(f)


def load_submission(code_file: str) -> object:
    """
    Load the submitted code as a module.
    Returns the module object if successful.
    """
    try:
        # Create a unique module name
        module_name = f"user_submission_{int(time.time())}"

        # Create module spec
        spec = importlib.util.spec_from_file_location(module_name, code_file)
        module = importlib.util.module_from_spec(spec)

        # Execute the module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        raise ImportError(f"Failed to import submission: {str(e)}")


def run_tests(module: object, test_data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], float]:
    """
    Run test cases against the submitted code.
    Returns: (success, test_results, score)
    """
    test_cases = test_data.get('test_cases', [])
    function_name = test_data.get('function_name', '')

    if not hasattr(module, function_name):
        raise AttributeError(f"Function '{function_name}' not found in submission")

    function = getattr(module, function_name)

    passed_tests = 0
    total_tests = len(test_cases)
    test_results = []

    for i, test_case in enumerate(test_cases):
        test_input = test_case.get('input', [])
        expected_output = test_case.get('expected_output')

        try:
            # Convert input to actual parameters
            if isinstance(test_input, list):
                actual_output = function(*test_input)
            elif isinstance(test_input, dict):
                actual_output = function(**test_input)
            else:
                actual_output = function(test_input)

            # Check if output matches expected output
            output_matches = actual_output == expected_output

            if output_matches:
                passed_tests += 1

            test_results.append({
                'test_case': i + 1,
                'passed': output_matches,
                'input': test_input,
                'expected_output': expected_output,
                'actual_output': actual_output
            })

        except Exception as e:
            test_results.append({
                'test_case': i + 1,
                'passed': False,
                'input': test_input,
                'expected_output': expected_output,
                'error': str(e),
                'traceback': traceback.format_exc()
            })

    score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    return passed_tests == total_tests, test_results, score


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            'status': 'error',
            'message': 'Insufficient arguments. Usage: python_evaluator.py <code_file> <test_data_file>'
        }))
        sys.exit(1)

    code_file = sys.argv[1]
    test_data_file = sys.argv[2]

    try:
        test_data = load_test_data(test_data_file)
        module = load_submission(code_file)
        success, test_results, score = run_tests(module, test_data)

        print(json.dumps({
            'status': 'success',
            'passed_all': success,
            'evaluation_score': score,
            'test_results': test_results
        }))

    except Exception as e:
        print(json.dumps({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()