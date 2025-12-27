#!/usr/bin/env python3
"""
Test runner for Lexi Simplify backend
"""

import unittest
import sys
import os
import coverage

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_tests_with_coverage():
    """Run tests with coverage reporting"""
    
    # Initialize coverage
    cov = coverage.Coverage()
    cov.start()
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Stop coverage and generate report
    cov.stop()
    cov.save()
    
    print("\n" + "="*50)
    print("COVERAGE REPORT")
    print("="*50)
    cov.report()
    
    # Generate HTML coverage report
    try:
        cov.html_report(directory='htmlcov')
        print(f"\nHTML coverage report generated in 'htmlcov' directory")
    except Exception as e:
        print(f"Could not generate HTML report: {e}")
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

def run_tests_simple():
    """Run tests without coverage"""
    
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1

def run_specific_test(test_name):
    """Run a specific test module or test case"""
    
    try:
        suite = unittest.TestLoader().loadTestsFromName(test_name)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return 0 if result.wasSuccessful() else 1
    except Exception as e:
        print(f"Error running test {test_name}: {e}")
        return 1

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--coverage':
            exit_code = run_tests_with_coverage()
        elif sys.argv[1] == '--help':
            print("Usage:")
            print("  python run_tests.py                 # Run all tests")
            print("  python run_tests.py --coverage      # Run tests with coverage")
            print("  python run_tests.py test_module     # Run specific test module")
            print("  python run_tests.py --help          # Show this help")
            exit_code = 0
        else:
            # Run specific test
            exit_code = run_specific_test(sys.argv[1])
    else:
        # Run all tests without coverage by default
        exit_code = run_tests_simple()
    
    sys.exit(exit_code)