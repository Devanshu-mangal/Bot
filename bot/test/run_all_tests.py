#!/usr/bin/env python3
"""Run all tests in the test/ directory"""

import sys
import os
import subprocess
import glob

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=" * 100)
    print("RUNNING ALL TESTS")
    print("=" * 100)
    
    # Find all test files
    test_files = glob.glob(os.path.join(os.path.dirname(__file__), "test_*.py"))
    test_files.sort()
    
    passed = 0
    failed = 0
    
    for test_file in test_files:
        test_name = os.path.basename(test_file)
        print(f"\n{'-' * 100}")
        print(f"RUNNING: {test_name}")
        print(f"{'-' * 100}")
        
        try:
            result = subprocess.run(
                [sys.executable, test_file],
                check=True,
                capture_output=False,
                text=True
            )
            passed += 1
            print(f"\n✅ {test_name} PASSED")
        except subprocess.CalledProcessError as e:
            failed += 1
            print(f"\n❌ {test_name} FAILED (exit code: {e.returncode})")
    
    print("\n" + "=" * 100)
    print(f"TEST SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 100)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
