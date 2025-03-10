#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

function loadTestData(testDataFile) {
    try {
        const data = fs.readFileSync(testDataFile, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        throw new Error(`Failed to load test data: ${error.message}`);
    }
}

function loadSubmission(codeFile) {
    try {
        const code = fs.readFileSync(codeFile, 'utf8');

        // Create a sandbox context
        const sandbox = {
            console: {
                log: console.log,
                error: console.error,
                warn: console.warn
            },
            exports: {},
            require: require
        };

        // Run the code in the sandbox
        vm.createContext(sandbox);
        vm.runInContext(code, sandbox);

        return sandbox;
    } catch (error) {
        throw new Error(`Failed to load submission: ${error.message}`);
    }
}

function runTests(sandbox, testData) {
    const testCases = testData.test_cases || [];
    const functionName = testData.function_name || '';

    // Get the function from the sandbox
    if (!sandbox[functionName] && !sandbox.exports[functionName]) {
        throw new Error(`Function '${functionName}' not found in submission`);
    }

    const func = sandbox[functionName] || sandbox.exports[functionName];

    let passedTests = 0;
    const totalTests = testCases.length;
    const testResults = [];

    for (let i = 0; i < testCases.length; i++) {
        const testCase = testCases[i];
        const testInput = testCase.input || [];
        const expectedOutput = testCase.expected_output;

        try {
            // Call the function with the input
            let actualOutput;
            if (Array.isArray(testInput)) {
                actualOutput = func(...testInput);
            } else if (typeof testInput === 'object') {
                actualOutput = func(testInput);
            } else {
                actualOutput = func(testInput);
            }

            // Check if output matches expected output
            // We use JSON.stringify for deep comparison
            const outputMatches = JSON.stringify(actualOutput) === JSON.stringify(expectedOutput);

            if (outputMatches) {
                passedTests++;
            }

            testResults.push({
                test_case: i + 1,
                passed: outputMatches,
                input: testInput,
                expected_output: expectedOutput,
                actual_output: actualOutput
            });

        } catch (error) {
            testResults.push({
                test_case: i + 1,
                passed: false,
                input: testInput,
                expected_output: expectedOutput,
                error: error.message,
                stack: error.stack
            });
        }
    }

    const score = totalTests > 0 ? (passedTests / totalTests) * 100 : 0;
    return {
        passed_all: passedTests === totalTests,
        test_results: testResults,
        score: score
    };
}

function main() {
    if (process.argv.length < 4) {
        console.log(JSON.stringify({
            status: 'error',
            message: 'Insufficient arguments. Usage: js_evaluator.js <code_file> <test_data_file>'
        }));
        process.exit(1);
    }

    const codeFile = process.argv[2];
    const testDataFile = process.argv[3];

    try {
        const testData = loadTestData(testDataFile);
        const sandbox = loadSubmission(codeFile);
        const result = runTests(sandbox, testData);

        console.log(JSON.stringify({
            status: 'success',
            passed_all: result.passed_all,
            evaluation_score: result.score,
            test_results: result.test_results
        }));

    } catch (error) {
        console.log(JSON.stringify({
            status: 'error',
            message: error.message,
            stack: error.stack
        }));
        process.exit(1);
    }
}

main();