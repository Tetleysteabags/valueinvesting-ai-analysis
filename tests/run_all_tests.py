#!/usr/bin/env python3
"""
Comprehensive test runner for Value Investing AI.
Run different types of tests based on your needs.
"""

import sys
import os
import subprocess
import time

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"🚀 {title}")
    print("="*60)

def print_test_menu():
    """Print the test menu."""
    print_header("Value Investing AI - Test Suite")
    print("Choose a test to run:")
    print()
    print("🔧 SETUP & VALIDATION TESTS:")
    print("  1. test_env.py              - Validate API keys and environment")
    print("  2. check_free_tier.py       - Test FMP free tier endpoints")
    print("  3. test_fmp_historical.py   - Test FMP historical data service")
    print()
    print("📊 DATA FETCHING TESTS:")
    print("  4. simple_test.py           - Basic test with 3 stocks (AAPL, MSFT, GOOGL)")
    print("  5. value_stocks_test.py     - Test with value-oriented stocks")
    print("  6. moderate_value_test.py   - Test with relaxed value criteria")
    print("  7. test_free_tier_run.py    - Full analysis with 35 test stocks")
    print()
    print("🧪 UNIT TESTS:")
    print("  8. test_stock_service.py    - Unit tests for stock service")
    print("  9. tests_fmp_client.py      - FMP API client tests")
    print()
    print("📈 BATCH TESTS:")
    print("  10. Run all validation tests (1-3)")
    print("  11. Run all data tests (4-7)")
    print("  12. Run all tests")
    print()
    print("  0. Exit")
    print()

def run_test(test_file, description=""):
    """Run a specific test file."""
    print(f"\n🔄 Running: {test_file}")
    if description:
        print(f"📝 {description}")
    print("-" * 40)
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              cwd=os.path.dirname(os.path.abspath(__file__)),
                              capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {test_file}: {e}")
        return False

def main():
    """Main test runner."""
    while True:
        print_test_menu()
        
        try:
            choice = input("Enter your choice (0-12): ").strip()
            
            if choice == "0":
                print("\n👋 Goodbye!")
                break
                
            elif choice == "1":
                run_test("test_env.py", "Validating API keys and environment setup")
                
            elif choice == "2":
                run_test("check_free_tier.py", "Testing FMP free tier endpoint availability")
                
            elif choice == "3":
                run_test("test_fmp_historical.py", "Testing FMP historical data service")
                
            elif choice == "4":
                run_test("simple_test.py", "Basic test with 3 major stocks (24 API calls)")
                
            elif choice == "5":
                run_test("value_stocks_test.py", "Test with value-oriented stocks (80 API calls)")
                
            elif choice == "6":
                run_test("moderate_value_test.py", "Test with relaxed value criteria (40 API calls)")
                
            elif choice == "7":
                print("\n⚠️  WARNING: This will use ~280 API calls!")
                confirm = input("Are you sure you want to run the full test? (y/N): ").strip().lower()
                if confirm == 'y':
                    run_test("test_free_tier_run.py", "Full analysis with 35 test stocks")
                else:
                    print("❌ Cancelled.")
                    
            elif choice == "8":
                run_test("test_stock_service.py", "Unit tests for stock service functionality")
                
            elif choice == "9":
                run_test("tests_fmp_client.py", "FMP API client unit tests")
                
            elif choice == "10":
                print_header("Running All Validation Tests")
                run_test("test_env.py", "Validating API keys")
                run_test("check_free_tier.py", "Testing FMP endpoints")
                run_test("test_fmp_historical.py", "Testing FMP historical data")
                print("\n✅ Validation tests completed!")
                
            elif choice == "11":
                print_header("Running All Data Tests")
                print("⚠️  This will use significant API calls!")
                confirm = input("Continue? (y/N): ").strip().lower()
                if confirm == 'y':
                    run_test("simple_test.py", "Basic test")
                    time.sleep(5)  # Wait between tests
                    run_test("value_stocks_test.py", "Value stocks test")
                    time.sleep(5)
                    run_test("moderate_value_test.py", "Moderate criteria test")
                    print("\n✅ Data tests completed!")
                else:
                    print("❌ Cancelled.")
                    
            elif choice == "12":
                print_header("Running All Tests")
                print("⚠️  This will use significant API calls and take time!")
                confirm = input("Continue? (y/N): ").strip().lower()
                if confirm == 'y':
                    # Validation tests
                    run_test("test_env.py")
                    run_test("check_free_tier.py")
                    run_test("test_fmp_historical.py")
                    
                    # Unit tests
                    run_test("test_stock_service.py")
                    run_test("tests_fmp_client.py")
                    
                    # Data tests (with delays)
                    time.sleep(5)
                    run_test("simple_test.py")
                    time.sleep(5)
                    run_test("value_stocks_test.py")
                    time.sleep(5)
                    run_test("moderate_value_test.py")
                    
                    print("\n✅ All tests completed!")
                else:
                    print("❌ Cancelled.")
                    
            else:
                print("❌ Invalid choice. Please enter a number between 0-12.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Test runner interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main() 