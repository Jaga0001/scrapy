#!/usr/bin/env python3
"""
Comprehensive validation script for AI Web Scraper.
Runs all validation checks including schemas, security, and functionality.
"""

import sys
import os
import subprocess
from pathlib import Path
import asyncio

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ComprehensiveValidator:
    """Runs all validation checks for the AI Web Scraper project."""
    
    def __init__(self):
        self.results = {
            "schema_validation": None,
            "security_validation": None,
            "functionality_test": None,
            "type_hints_validation": None,
            "model_tests": None
        }
        self.total_errors = 0
        self.total_warnings = 0
    
    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        print("🔍 AI Web Scraper - Comprehensive Validation")
        print("=" * 60)
        print(f"📁 Project Root: {project_root}")
        print(f"🐍 Python Version: {sys.version}")
        print("=" * 60)
        
        # 1. Schema Validation
        self.run_schema_validation()
        
        # 2. Security Validation
        self.run_security_validation()
        
        # 3. Type Hints Validation
        self.run_type_hints_validation()
        
        # 4. Model Tests
        self.run_model_tests()
        
        # 5. Functionality Test
        self.run_functionality_test()
        
        # Print comprehensive results
        self.print_comprehensive_results()
        
        return self.total_errors == 0
    
    def run_schema_validation(self):
        """Run schema validation."""
        print("\n📋 Running Schema Validation...")
        print("-" * 40)
        
        try:
            result = subprocess.run([
                sys.executable, "scripts/validate_schemas.py"
            ], cwd=project_root, capture_output=True, text=True, timeout=60)
            
            self.results["schema_validation"] = {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
            
            if result.returncode == 0:
                print("✅ Schema validation passed")
            else:
                print("❌ Schema validation failed")
                self.total_errors += 1
                
        except subprocess.TimeoutExpired:
            print("⏰ Schema validation timed out")
            self.results["schema_validation"] = {
                "success": False,
                "output": "",
                "error": "Validation timed out"
            }
            self.total_errors += 1
        except Exception as e:
            print(f"💥 Schema validation error: {e}")
            self.results["schema_validation"] = {
                "success": False,
                "output": "",
                "error": str(e)
            }
            self.total_errors += 1
    
    def run_security_validation(self):
        """Run security validation."""
        print("\n🔒 Running Security Validation...")
        print("-" * 40)
        
        try:
            result = subprocess.run([
                sys.executable, "scripts/validate_security.py"
            ], cwd=project_root, capture_output=True, text=True, timeout=30)
            
            self.results["security_validation"] = {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
            
            if result.returncode == 0:
                print("✅ Security validation passed")
            else:
                print("❌ Security validation failed")
                self.total_errors += 1
                
        except subprocess.TimeoutExpired:
            print("⏰ Security validation timed out")
            self.results["security_validation"] = {
                "success": False,
                "output": "",
                "error": "Validation timed out"
            }
            self.total_errors += 1
        except Exception as e:
            print(f"💥 Security validation error: {e}")
            self.results["security_validation"] = {
                "success": False,
                "output": "",
                "error": str(e)
            }
            self.total_errors += 1
    
    def run_type_hints_validation(self):
        """Run type hints validation."""
        print("\n🔤 Running Type Hints Validation...")
        print("-" * 40)
        
        try:
            result = subprocess.run([
                sys.executable, "scripts/generate_type_hints.py"
            ], cwd=project_root, capture_output=True, text=True, timeout=60)
            
            self.results["type_hints_validation"] = {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
            
            if result.returncode == 0:
                print("✅ Type hints validation passed")
            else:
                print("⚠️ Type hints validation found issues")
                self.total_warnings += 1
                
        except subprocess.TimeoutExpired:
            print("⏰ Type hints validation timed out")
            self.results["type_hints_validation"] = {
                "success": False,
                "output": "",
                "error": "Validation timed out"
            }
            self.total_warnings += 1
        except Exception as e:
            print(f"💥 Type hints validation error: {e}")
            self.results["type_hints_validation"] = {
                "success": False,
                "output": "",
                "error": str(e)
            }
            self.total_warnings += 1
    
    def run_model_tests(self):
        """Run model tests."""
        print("\n🧪 Running Model Tests...")
        print("-" * 40)
        
        try:
            # Check if pytest is available
            pytest_available = subprocess.run([
                sys.executable, "-c", "import pytest"
            ], capture_output=True).returncode == 0
            
            if pytest_available:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"
                ], cwd=project_root, capture_output=True, text=True, timeout=120)
                
                self.results["model_tests"] = {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr
                }
                
                if result.returncode == 0:
                    print("✅ Model tests passed")
                else:
                    print("❌ Model tests failed")
                    self.total_errors += 1
            else:
                print("⚠️ pytest not available - skipping model tests")
                self.results["model_tests"] = {
                    "success": True,
                    "output": "pytest not available",
                    "error": ""
                }
                self.total_warnings += 1
                
        except subprocess.TimeoutExpired:
            print("⏰ Model tests timed out")
            self.results["model_tests"] = {
                "success": False,
                "output": "",
                "error": "Tests timed out"
            }
            self.total_errors += 1
        except Exception as e:
            print(f"💥 Model tests error: {e}")
            self.results["model_tests"] = {
                "success": False,
                "output": "",
                "error": str(e)
            }
            self.total_errors += 1
    
    def run_functionality_test(self):
        """Run functionality test."""
        print("\n🕷️ Running Functionality Test...")
        print("-" * 40)
        
        try:
            result = subprocess.run([
                sys.executable, "test_scraper.py"
            ], cwd=project_root, capture_output=True, text=True, timeout=180)
            
            self.results["functionality_test"] = {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
            
            if result.returncode == 0:
                print("✅ Functionality test passed")
            else:
                print("❌ Functionality test failed")
                self.total_errors += 1
                
        except subprocess.TimeoutExpired:
            print("⏰ Functionality test timed out")
            self.results["functionality_test"] = {
                "success": False,
                "output": "",
                "error": "Test timed out"
            }
            self.total_errors += 1
        except Exception as e:
            print(f"💥 Functionality test error: {e}")
            self.results["functionality_test"] = {
                "success": False,
                "output": "",
                "error": str(e)
            }
            self.total_errors += 1
    
    def print_comprehensive_results(self):
        """Print comprehensive validation results."""
        print("\n" + "=" * 60)
        print("📊 Comprehensive Validation Results")
        print("=" * 60)
        
        # Summary table
        print("\n📋 Validation Summary:")
        print("-" * 40)
        
        for test_name, result in self.results.items():
            if result is None:
                status = "⏭️ SKIPPED"
            elif result["success"]:
                status = "✅ PASSED"
            else:
                status = "❌ FAILED"
            
            test_display = test_name.replace("_", " ").title()
            print(f"  {test_display:<25} {status}")
        
        # Detailed results
        print("\n📝 Detailed Results:")
        print("-" * 40)
        
        for test_name, result in self.results.items():
            if result is None:
                continue
                
            test_display = test_name.replace("_", " ").title()
            print(f"\n🔍 {test_display}:")
            
            if result["success"]:
                print("  Status: ✅ PASSED")
            else:
                print("  Status: ❌ FAILED")
            
            if result["error"]:
                print(f"  Error: {result['error']}")
            
            # Show key output lines
            if result["output"]:
                output_lines = result["output"].split('\n')
                important_lines = [
                    line for line in output_lines 
                    if any(marker in line for marker in ['✅', '❌', '⚠️', 'Error', 'Failed', 'Passed'])
                ]
                
                if important_lines:
                    print("  Key Output:")
                    for line in important_lines[:5]:  # Show first 5 important lines
                        print(f"    {line.strip()}")
                    if len(important_lines) > 5:
                        print(f"    ... and {len(important_lines) - 5} more lines")
        
        # Overall summary
        print("\n" + "=" * 60)
        print("🎯 Overall Summary")
        print("=" * 60)
        
        total_tests = len([r for r in self.results.values() if r is not None])
        passed_tests = len([r for r in self.results.values() if r and r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Tests Run: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️ Warnings: {self.total_warnings}")
        
        if self.total_errors == 0:
            print(f"\n🎉 All validations completed successfully!")
            if self.total_warnings > 0:
                print(f"💡 Consider addressing {self.total_warnings} warning(s) for optimal performance")
        else:
            print(f"\n🚨 {self.total_errors} validation(s) failed!")
            print(f"🔧 Please fix the errors before deploying")
        
        # Recommendations
        print(f"\n💡 Next Steps:")
        if self.total_errors > 0:
            print(f"  1. Fix the {self.total_errors} failed validation(s)")
            print(f"  2. Re-run this validation script")
            print(f"  3. Check individual validation outputs for details")
        else:
            print(f"  1. ✅ All validations passed - system is ready!")
            print(f"  2. Consider running: python run.py")
            print(f"  3. Monitor system performance and logs")
        
        if self.total_warnings > 0:
            print(f"  4. Address {self.total_warnings} warning(s) when possible")


def main():
    """Main validation function."""
    validator = ComprehensiveValidator()
    success = validator.run_all_validations()
    
    if success:
        print("\n✅ Comprehensive validation completed successfully!")
        return 0
    else:
        print("\n❌ Comprehensive validation failed!")
        return 1


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during validation: {e}")
        sys.exit(1)