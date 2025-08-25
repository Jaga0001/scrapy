#!/usr/bin/env python3
"""
Security audit script for the AI Web Scraper project.

This script performs automated security checks on the codebase and configuration
to identify potential security vulnerabilities and misconfigurations.
"""

import os
import re
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.security_validator import SecurityConfigValidator, validate_environment_file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SecurityAuditor:
    """Comprehensive security auditor for the web scraper project."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": []
        }
    
    def run_full_audit(self) -> Dict[str, Any]:
        """Run complete security audit."""
        logger.info("Starting comprehensive security audit...")
        
        # Check environment files
        self._audit_environment_files()
        
        # Check source code for hardcoded secrets
        self._audit_source_code()
        
        # Check configuration files
        self._audit_configuration_files()
        
        # Check test files for security issues
        self._audit_test_files()
        
        # Check file permissions
        self._audit_file_permissions()
        
        # Generate report
        return self._generate_report()
    
    def _audit_environment_files(self):
        """Audit environment configuration files."""
        logger.info("Auditing environment files...")
        
        env_files = ['.env', '.env.example', '.env.local', '.env.production']
        
        for env_file in env_files:
            env_path = self.project_root / env_file
            if env_path.exists():
                results = validate_environment_file(str(env_path))
                
                for error in results["errors"]:
                    self.issues["critical"].append({
                        "type": "environment_config",
                        "file": env_file,
                        "issue": error,
                        "severity": "critical"
                    })
                
                for warning in results["warnings"]:
                    self.issues["medium"].append({
                        "type": "environment_config",
                        "file": env_file,
                        "issue": warning,
                        "severity": "medium"
                    })
    
    def _audit_source_code(self):
        """Audit source code for hardcoded secrets and security issues."""
        logger.info("Auditing source code...")
        
        # Patterns to look for
        secret_patterns = [
            (r'api_key\s*=\s*["\'][^"\']{20,}["\']', "Potential hardcoded API key"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Potential hardcoded password"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Potential hardcoded secret"),
            (r'token\s*=\s*["\'][^"\']{20,}["\']', "Potential hardcoded token"),
            (r'AIza[0-9A-Za-z_-]{35}', "Google API key pattern"),
            (r'sk-[0-9A-Za-z]{48}', "OpenAI API key pattern"),
            (r'postgresql://[^:]+:[^@]+@', "Database URL with credentials"),
            (r'mysql://[^:]+:[^@]+@', "MySQL URL with credentials"),
            (r'mongodb://[^:]+:[^@]+@', "MongoDB URL with credentials"),
        ]
        
        # Files to check
        python_files = list(self.project_root.rglob("*.py"))
        config_files = list(self.project_root.rglob("*.json")) + list(self.project_root.rglob("*.yaml")) + list(self.project_root.rglob("*.yml"))
        
        all_files = python_files + config_files
        
        for file_path in all_files:
            # Skip certain directories
            if any(skip_dir in str(file_path) for skip_dir in ['.git', '__pycache__', '.pytest_cache', 'venv', 'node_modules']):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for pattern, description in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Skip test files and example files for some patterns
                        if 'test' in str(file_path).lower() or 'example' in str(file_path).lower():
                            severity = "low"
                        else:
                            severity = "high"
                        
                        self.issues[severity].append({
                            "type": "hardcoded_secret",
                            "file": str(file_path.relative_to(self.project_root)),
                            "issue": description,
                            "pattern": pattern,
                            "match": match.group()[:50] + "..." if len(match.group()) > 50 else match.group(),
                            "line": content[:match.start()].count('\n') + 1,
                            "severity": severity
                        })
            
            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")
    
    def _audit_configuration_files(self):
        """Audit configuration files for security issues."""
        logger.info("Auditing configuration files...")
        
        # Check settings.py
        settings_file = self.project_root / "config" / "settings.py"
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for insecure defaults
                insecure_patterns = [
                    (r'debug\s*=\s*True', "Debug mode enabled by default"),
                    (r'SECRET_KEY\s*=\s*["\'][^"\']{1,20}["\']', "Short secret key"),
                    (r'ALLOWED_HOSTS\s*=\s*\[\s*["\']?\*["\']?\s*\]', "Wildcard in ALLOWED_HOSTS"),
                ]
                
                for pattern, description in insecure_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        self.issues["medium"].append({
                            "type": "configuration",
                            "file": "config/settings.py",
                            "issue": description,
                            "severity": "medium"
                        })
            
            except Exception as e:
                logger.warning(f"Could not read settings file: {e}")
    
    def _audit_test_files(self):
        """Audit test files for security issues."""
        logger.info("Auditing test files...")
        
        test_files = list(self.project_root.rglob("test_*.py")) + list(self.project_root.rglob("*_test.py"))
        
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for hardcoded credentials in tests
                if re.search(r'password\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
                    # Only flag if it's not obviously a test value
                    if not any(test_indicator in content.lower() for test_indicator in ['test', 'mock', 'fake', 'dummy']):
                        self.issues["medium"].append({
                            "type": "test_security",
                            "file": str(test_file.relative_to(self.project_root)),
                            "issue": "Potential real credentials in test file",
                            "severity": "medium"
                        })
            
            except Exception as e:
                logger.warning(f"Could not read test file {test_file}: {e}")
    
    def _audit_file_permissions(self):
        """Audit file permissions for security issues."""
        logger.info("Auditing file permissions...")
        
        if os.name != 'posix':
            logger.info("Skipping file permission audit on non-Unix system")
            return
        
        import stat
        
        sensitive_files = ['.env', '.env.local', '.env.production', 'config/secrets.json']
        
        for file_name in sensitive_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                file_stat = file_path.stat()
                
                # Check if file is readable by others
                if file_stat.st_mode & stat.S_IROTH:
                    self.issues["high"].append({
                        "type": "file_permissions",
                        "file": file_name,
                        "issue": "Sensitive file is readable by others",
                        "severity": "high"
                    })
                
                # Check if file is writable by others
                if file_stat.st_mode & stat.S_IWOTH:
                    self.issues["critical"].append({
                        "type": "file_permissions",
                        "file": file_name,
                        "issue": "Sensitive file is writable by others",
                        "severity": "critical"
                    })
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security audit report."""
        total_issues = sum(len(issues) for issues in self.issues.values())
        
        report = {
            "summary": {
                "total_issues": total_issues,
                "critical": len(self.issues["critical"]),
                "high": len(self.issues["high"]),
                "medium": len(self.issues["medium"]),
                "low": len(self.issues["low"]),
                "info": len(self.issues["info"])
            },
            "issues": self.issues,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations based on found issues."""
        recommendations = []
        
        if self.issues["critical"]:
            recommendations.append("🚨 CRITICAL: Address critical security issues immediately before deployment")
        
        if any("hardcoded" in str(issue) for issue in self.issues["high"]):
            recommendations.append("🔑 Move all hardcoded secrets to environment variables")
        
        if any("environment" in str(issue) for issue in self.issues["medium"]):
            recommendations.append("⚙️ Review and secure environment configuration")
        
        if any("permission" in str(issue) for issue in self.issues["high"]):
            recommendations.append("🔒 Fix file permissions for sensitive files (chmod 600)")
        
        recommendations.extend([
            "🛡️ Use the SecurityConfigValidator in your application startup",
            "🔐 Generate secure secrets with: openssl rand -hex 32",
            "📝 Review the security_recommendations.md file for detailed guidance",
            "🧪 Run security tests regularly in your CI/CD pipeline"
        ])
        
        return recommendations


def print_report(report: Dict[str, Any]):
    """Print formatted security audit report."""
    print("\n" + "="*80)
    print("🔍 SECURITY AUDIT REPORT")
    print("="*80)
    
    summary = report["summary"]
    print(f"\n📊 SUMMARY:")
    print(f"   Total Issues: {summary['total_issues']}")
    print(f"   🚨 Critical: {summary['critical']}")
    print(f"   🔴 High: {summary['high']}")
    print(f"   🟡 Medium: {summary['medium']}")
    print(f"   🔵 Low: {summary['low']}")
    print(f"   ℹ️  Info: {summary['info']}")
    
    # Print issues by severity
    for severity in ["critical", "high", "medium", "low", "info"]:
        issues = report["issues"][severity]
        if issues:
            severity_icons = {
                "critical": "🚨",
                "high": "🔴",
                "medium": "🟡",
                "low": "🔵",
                "info": "ℹ️"
            }
            
            print(f"\n{severity_icons[severity]} {severity.upper()} ISSUES:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue['issue']}")
                print(f"      File: {issue['file']}")
                if 'line' in issue:
                    print(f"      Line: {issue['line']}")
                if 'match' in issue:
                    print(f"      Match: {issue['match']}")
                print()
    
    # Print recommendations
    print("💡 RECOMMENDATIONS:")
    for rec in report["recommendations"]:
        print(f"   {rec}")
    
    print("\n" + "="*80)


def main():
    """Main function to run security audit."""
    project_root = Path(__file__).parent.parent
    
    auditor = SecurityAuditor(project_root)
    report = auditor.run_full_audit()
    
    # Print report to console
    print_report(report)
    
    # Save report to file
    report_file = project_root / "security_audit_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Detailed report saved to: {report_file}")
    
    # Exit with error code if critical or high issues found
    if report["summary"]["critical"] > 0 or report["summary"]["high"] > 0:
        logger.error("Critical or high severity security issues found!")
        sys.exit(1)
    
    logger.info("Security audit completed successfully!")


if __name__ == "__main__":
    main()