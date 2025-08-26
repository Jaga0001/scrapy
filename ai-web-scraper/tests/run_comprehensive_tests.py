#!/usr/bin/env python3
"""
Comprehensive test runner for the AI Web Scraper project.

This script runs all test suites with proper configuration and generates
comprehensive coverage reports.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any


class TestRunner:
    """Comprehensive test runner with coverage reporting."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_results: Dict[str, Any] = {}
        
    def run_unit_tests(self, verbose: bool = False) -> bool:
        """Run unit tests."""
        print("🧪 Running Unit Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit/",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/unit",
            "--cov-report=xml:coverage-unit.xml",
            "-m", "not integration and not performance",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = self._run_command(cmd, "Unit Tests")
        self.test_results['unit_tests'] = result
        return result['success']
    
    def run_integration_tests(self, verbose: bool = False) -> bool:
        """Run integration tests."""
        print("🔗 Running Integration Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/integration/",
            "--cov=src",
            "--cov-append",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/integration",
            "--cov-report=xml:coverage-integration.xml",
            "-m", "integration",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = self._run_command(cmd, "Integration Tests")
        self.test_results['integration_tests'] = result
        return result['success']
    
    def run_performance_tests(self, verbose: bool = False) -> bool:
        """Run performance tests."""
        print("⚡ Running Performance Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/performance/",
            "--cov=src",
            "--cov-append",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/performance",
            "--cov-report=xml:coverage-performance.xml",
            "-m", "performance",
            "--tb=short",
            "--durations=10"  # Show 10 slowest tests
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = self._run_command(cmd, "Performance Tests")
        self.test_results['performance_tests'] = result
        return result['success']
    
    def run_e2e_tests(self, verbose: bool = False) -> bool:
        """Run end-to-end tests."""
        print("🎯 Running End-to-End Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/integration/test_end_to_end_workflows.py",
            "--cov=src",
            "--cov-append",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/e2e",
            "--cov-report=xml:coverage-e2e.xml",
            "-m", "not performance",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = self._run_command(cmd, "End-to-End Tests")
        self.test_results['e2e_tests'] = result
        return result['success']
    
    def run_all_tests(self, verbose: bool = False) -> bool:
        """Run all test suites."""
        print("🚀 Running All Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/all",
            "--cov-report=xml:coverage-all.xml",
            "--tb=short",
            "--durations=20"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = self._run_command(cmd, "All Tests")
        self.test_results['all_tests'] = result
        return result['success']
    
    def run_coverage_report(self) -> bool:
        """Generate comprehensive coverage report."""
        print("📊 Generating Coverage Report...")
        
        # Combine coverage data
        combine_cmd = [sys.executable, "-m", "coverage", "combine"]
        self._run_command(combine_cmd, "Coverage Combine", check_success=False)
        
        # Generate HTML report
        html_cmd = [
            sys.executable, "-m", "coverage", "html",
            "--directory=htmlcov/comprehensive",
            "--title=AI Web Scraper Comprehensive Coverage"
        ]
        html_result = self._run_command(html_cmd, "HTML Coverage Report")
        
        # Generate XML report
        xml_cmd = [sys.executable, "-m", "coverage", "xml", "-o", "coverage-comprehensive.xml"]
        xml_result = self._run_command(xml_cmd, "XML Coverage Report")
        
        # Generate text report
        text_cmd = [sys.executable, "-m", "coverage", "report", "--show-missing"]
        text_result = self._run_command(text_cmd, "Text Coverage Report")
        
        return html_result['success'] and xml_result['success'] and text_result['success']
    
    def run_linting(self) -> bool:
        """Run code linting checks."""
        print("🔍 Running Code Linting...")
        
        # Run flake8
        flake8_cmd = [sys.executable, "-m", "flake8", "src/", "tests/", "--max-line-length=88"]
        flake8_result = self._run_command(flake8_cmd, "Flake8 Linting", check_success=False)
        
        # Run black check
        black_cmd = [sys.executable, "-m", "black", "--check", "src/", "tests/"]
        black_result = self._run_command(black_cmd, "Black Formatting Check", check_success=False)
        
        # Run isort check
        isort_cmd = [sys.executable, "-m", "isort", "--check-only", "src/", "tests/"]
        isort_result = self._run_command(isort_cmd, "Import Sorting Check", check_success=False)
        
        self.test_results['linting'] = {
            'flake8': flake8_result,
            'black': black_result,
            'isort': isort_result
        }
        
        return flake8_result['success'] and black_result['success'] and isort_result['success']
    
    def run_security_checks(self) -> bool:
        """Run security checks."""
        print("🔒 Running Security Checks...")
        
        # Run bandit security linter
        bandit_cmd = [
            sys.executable, "-m", "bandit", "-r", "src/",
            "-f", "json", "-o", "security-report.json"
        ]
        bandit_result = self._run_command(bandit_cmd, "Bandit Security Check", check_success=False)
        
        # Run safety check for dependencies
        safety_cmd = [sys.executable, "-m", "safety", "check", "--json"]
        safety_result = self._run_command(safety_cmd, "Safety Dependency Check", check_success=False)
        
        self.test_results['security'] = {
            'bandit': bandit_result,
            'safety': safety_result
        }
        
        return bandit_result['success'] and safety_result['success']
    
    def generate_test_report(self) -> None:
        """Generate comprehensive test report."""
        print("📋 Generating Test Report...")
        
        report_path = self.project_root / "test-report.md"
        
        with open(report_path, 'w') as f:
            f.write("# AI Web Scraper Test Report\n\n")
            f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Test Results Summary\n\n")
            
            total_tests = 0
            passed_tests = 0
            
            for test_type, result in self.test_results.items():
                if isinstance(result, dict) and 'success' in result:
                    status = "✅ PASSED" if result['success'] else "❌ FAILED"
                    f.write(f"- **{test_type.replace('_', ' ').title()}**: {status}\n")
                    
                    if 'tests_run' in result:
                        total_tests += result['tests_run']
                        if result['success']:
                            passed_tests += result['tests_run']
            
            f.write(f"\n**Overall**: {passed_tests}/{total_tests} tests passed\n\n")
            
            f.write("## Coverage Information\n\n")
            f.write("Coverage reports are available in the following locations:\n")
            f.write("- HTML Report: `htmlcov/comprehensive/index.html`\n")
            f.write("- XML Report: `coverage-comprehensive.xml`\n\n")
            
            f.write("## Test Categories\n\n")
            f.write("### Unit Tests\n")
            f.write("- Location: `tests/unit/`\n")
            f.write("- Purpose: Test individual components in isolation\n")
            f.write("- Coverage: Individual module testing\n\n")
            
            f.write("### Integration Tests\n")
            f.write("- Location: `tests/integration/`\n")
            f.write("- Purpose: Test component interactions\n")
            f.write("- Coverage: Cross-module functionality\n\n")
            
            f.write("### Performance Tests\n")
            f.write("- Location: `tests/performance/`\n")
            f.write("- Purpose: Test system performance under load\n")
            f.write("- Coverage: Concurrent processing, scalability\n\n")
            
            f.write("### End-to-End Tests\n")
            f.write("- Location: `tests/integration/test_end_to_end_workflows.py`\n")
            f.write("- Purpose: Test complete workflows\n")
            f.write("- Coverage: Full system integration\n\n")
            
            if 'linting' in self.test_results:
                f.write("## Code Quality\n\n")
                linting = self.test_results['linting']
                f.write(f"- **Flake8**: {'✅ PASSED' if linting['flake8']['success'] else '❌ FAILED'}\n")
                f.write(f"- **Black**: {'✅ PASSED' if linting['black']['success'] else '❌ FAILED'}\n")
                f.write(f"- **isort**: {'✅ PASSED' if linting['isort']['success'] else '❌ FAILED'}\n\n")
            
            if 'security' in self.test_results:
                f.write("## Security\n\n")
                security = self.test_results['security']
                f.write(f"- **Bandit**: {'✅ PASSED' if security['bandit']['success'] else '❌ FAILED'}\n")
                f.write(f"- **Safety**: {'✅ PASSED' if security['safety']['success'] else '❌ FAILED'}\n\n")
        
        print(f"📋 Test report generated: {report_path}")
    
    def _run_command(self, cmd: List[str], description: str, check_success: bool = True) -> Dict[str, Any]:
        """Run a command and capture results."""
        print(f"  Running {description}...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.returncode == 0 or not check_success
            
            if success:
                print(f"  ✅ {description} completed in {duration:.2f}s")
            else:
                print(f"  ❌ {description} failed in {duration:.2f}s")
                if result.stderr:
                    print(f"     Error: {result.stderr[:200]}...")
            
            return {
                'success': success,
                'returncode': result.returncode,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'tests_run': self._extract_test_count(result.stdout)
            }
            
        except subprocess.TimeoutExpired:
            print(f"  ⏰ {description} timed out after 5 minutes")
            return {
                'success': False,
                'returncode': -1,
                'duration': 300,
                'stdout': '',
                'stderr': 'Command timed out',
                'tests_run': 0
            }
        except Exception as e:
            print(f"  💥 {description} failed with exception: {e}")
            return {
                'success': False,
                'returncode': -1,
                'duration': 0,
                'stdout': '',
                'stderr': str(e),
                'tests_run': 0
            }
    
    def _extract_test_count(self, output: str) -> int:
        """Extract test count from pytest output."""
        import re
        
        # Look for patterns like "5 passed" or "3 failed, 2 passed"
        patterns = [
            r'(\d+) passed',
            r'(\d+) failed',
            r'(\d+) error',
            r'(\d+) skipped'
        ]
        
        total = 0
        for pattern in patterns:
            matches = re.findall(pattern, output)
            for match in matches:
                total += int(match)
        
        return total


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Comprehensive test runner for AI Web Scraper")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")
    parser.add_argument("--lint", action="store_true", help="Run linting checks only")
    parser.add_argument("--security", action="store_true", help="Run security checks only")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report only")
    parser.add_argument("--all", action="store_true", help="Run all tests and checks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--report", action="store_true", help="Generate test report")
    
    args = parser.parse_args()
    
    # Default to running all tests if no specific option is provided
    if not any([args.unit, args.integration, args.performance, args.e2e, 
                args.lint, args.security, args.coverage, args.all]):
        args.all = True
    
    project_root = Path(__file__).parent.parent
    runner = TestRunner(project_root)
    
    print("🧪 AI Web Scraper Comprehensive Test Suite")
    print("=" * 50)
    
    success = True
    
    if args.unit or args.all:
        success &= runner.run_unit_tests(args.verbose)
    
    if args.integration or args.all:
        success &= runner.run_integration_tests(args.verbose)
    
    if args.performance or args.all:
        success &= runner.run_performance_tests(args.verbose)
    
    if args.e2e or args.all:
        success &= runner.run_e2e_tests(args.verbose)
    
    if args.lint or args.all:
        success &= runner.run_linting()
    
    if args.security or args.all:
        success &= runner.run_security_checks()
    
    if args.coverage or args.all:
        success &= runner.run_coverage_report()
    
    if args.report or args.all:
        runner.generate_test_report()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests and checks passed!")
        sys.exit(0)
    else:
        print("❌ Some tests or checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()