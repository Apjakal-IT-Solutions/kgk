# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Test runner for KGK Customisations
Runs all test suites and generates coverage report
"""

import unittest
import sys
import os


def run_all_tests(verbosity=2):
    """Run all test suites"""
    
    # Import all test modules
    from kgk_customisations.tests import (
        test_cash_document,
        test_daily_cash_balance,
        test_integration
    )
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all tests
    suite.addTests(loader.loadTestsFromModule(test_cash_document))
    suite.addTests(loader.loadTestsFromModule(test_daily_cash_balance))
    suite.addTests(loader.loadTestsFromModule(test_integration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result


def run_specific_test(test_name, verbosity=2):
    """Run a specific test class or method"""
    
    if "." in test_name:
        # Format: module.TestClass.test_method
        parts = test_name.split(".")
        module_name = parts[0]
        
        module = __import__(f"kgk_customisations.tests.{module_name}", fromlist=[parts[1]])
        
        if len(parts) == 2:
            # Run entire test class
            test_class = getattr(module, parts[1])
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        else:
            # Run specific test method
            test_class = getattr(module, parts[1])
            suite = unittest.TestSuite()
            suite.addTest(test_class(parts[2]))
    else:
        # Run entire module
        module = __import__(f"kgk_customisations.tests.{test_name}", fromlist=['*'])
        suite = unittest.TestLoader().loadTestsFromModule(module)
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        result = run_specific_test(test_name)
    else:
        # Run all tests
        result = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
