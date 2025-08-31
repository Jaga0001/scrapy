#!/usr/bin/env python3
"""
Security validation script for AI Web Scraper.
Performs comprehensive security checks on configuration and code.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Any
import subprocess

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.utils.security_config import SecurityConfig
except ImportError:
    print("⚠️ Could not import SecurityConfig. Running basic validation only.")
    SecurityConfig = None

class SecurityValidator:
    """Comprehensive security validation for the web scraper project."""
    
    def __init__(self):
        self.project_root = project_root
        self.issues = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': [],
            'info': []
        }
    
    def validate_all(self) -> Dict[str, List[str]]:
        """Run all security validations."""
        print("🔍 Running comprehensive security validation...")
        print("=" * 60)
        
        self.validate_environment_variables()
        self.validate_code_security()
        self.validate_file_permissions()
        self.validate_dependencies()
        self.validate_configuration_files()
        
        return self.issues
    
    def validate_environment_variables(self):
        """Validate environment variable security."""
        print("\n📋 Validating Environment Variables...")
        
        if SecurityConfig:
            env_issues = SecurityConfig.validate_environment()
            self.issues['critical'].extend(env_issues.get('critical', []))
            self.issues['medium'].extend(env_issues.get('warnings', []))
            self.issues['info'].extend(env_issues.get('info', []))
        
        # Additional environment checks
        env_file = self.project_root / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
                
                # Check for common insecure patterns
                insecure_patterns = [
                    (r'password\s*=\s*["\']?admin["\']?', 'Default admin password detected'),
                    (r'secret\s*=\s*["\']?secret["\']?', 'Default secret value detected'),
                    (r'key\s*=\s*["\']?key["\']?', 'Default key value detected'),
                    (r'token\s*=\s*["\']?token["\']?', 'Default token value detected'),
                    (r'DEBUG\s*=\s*[Tt]rue', 'Debug mode enabled'),
                    (r'0\.0\.0\.0', 'Binding to all interfaces (0.0.0.0)'),
                ]
                
                for pattern, message in insecure_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        self.issues['medium'].append(f"Environment: {message}")
    
    def validate_code_security(self):
        """Validate code for security issues."""
        print("🔍 Scanning Code for Security Issues...")
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            if ".venv" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self._check_file_security(file_path, content)
            except Exception as e:
                self.issues['low'].append(f"Could not read {file_path}: {e}")
    
    def _check_file_security(self, file_path: Path, content: str):
        """Check individual file for security issues."""
        relative_path = file_path.relative_to(self.project_root)
        
        # Security patterns to check
        security_patterns = [
            # Critical issues
            (r'password\s*=\s*["\'][^"\']+["\']', 'critical', 'Hardcoded password'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'critical', 'Hardcoded API key'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'critical', 'Hardcoded secret'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'critical', 'Hardcoded token'),
            
            # High risk issues
            (r'eval\s*\(', 'high', 'Use of eval() function'),
            (r'exec\s*\(', 'high', 'Use of exec() function'),
            (r'subprocess\.call\([^)]*shell\s*=\s*True', 'high', 'Shell injection risk'),
            (r'os\.system\s*\(', 'high', 'Command injection risk'),
            
            # Medium risk issues
            (r'pickle\.loads?\s*\(', 'medium', 'Unsafe pickle usage'),
            (r'yaml\.load\s*\([^)]*Loader\s*=\s*yaml\.Loader', 'medium', 'Unsafe YAML loading'),
            (r'requests\.get\([^)]*verify\s*=\s*False', 'medium', 'SSL verification disabled'),
            (r'urllib\.request\.urlopen\([^)]*context\s*=\s*ssl\._create_unverified_context', 'medium', 'SSL verification disabled'),
            
            # Low risk issues
            (r'print\s*\([^)]*password', 'low', 'Password in print statement'),
            (r'print\s*\([^)]*secret', 'low', 'Secret in print statement'),
            (r'print\s*\([^)]*token', 'low', 'Token in print statement'),
            (r'logging\.[^(]*\([^)]*password', 'low', 'Password in log statement'),
        ]
        
        for pattern, severity, message in security_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                self.issues[severity].append(
                    f"{relative_path}:{line_num} - {message}: {match.group()[:50]}..."
                )
    
    def validate_file_permissions(self):
        """Check file permissions for security issues."""
        print("🔐 Checking File Permissions...")
        
        sensitive_files = [
            ".env",
            ".env.production",
            ".env.staging",
            "config/secrets.json",
            "private_key.pem",
            "certificate.crt"
        ]
        
        for file_name in sensitive_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                try:
                    stat_info = file_path.stat()
                    permissions = oct(stat_info.st_mode)[-3:]
                    
                    # Check if file is readable by others
                    if permissions[2] in ['4', '5', '6', '7']:
                        self.issues['high'].append(
                            f"File {file_name} is readable by others (permissions: {permissions})"
                        )
                    
                    # Check if file is writable by group or others
                    if permissions[1] in ['2', '3', '6', '7'] or permissions[2] in ['2', '3', '6', '7']:
                        self.issues['medium'].append(
                            f"File {file_name} is writable by group/others (permissions: {permissions})"
                        )
                        
                except Exception as e:
                    self.issues['low'].append(f"Could not check permissions for {file_name}: {e}")
    
    def validate_dependencies(self):
        """Check dependencies for known vulnerabilities."""
        print("📦 Checking Dependencies for Vulnerabilities...")
        
        requirements_files = [
            "requirements.txt",
            "pyproject.toml",
            "Pipfile"
        ]
        
        for req_file in requirements_files:
            file_path = self.project_root / req_file
            if file_path.exists():
                self.issues['info'].append(f"Found dependency file: {req_file}")
                
                # Check for potentially insecure packages
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                        # Known packages with security considerations
                        risky_packages = [
                            ('pickle', 'Pickle can execute arbitrary code'),
                            ('yaml', 'YAML loading can be unsafe'),
                            ('requests', 'Ensure SSL verification is enabled'),
                            ('urllib3', 'Check SSL/TLS configuration'),
                        ]
                        
                        for package, warning in risky_packages:
                            if package in content.lower():
                                self.issues['info'].append(f"Dependency {package}: {warning}")
                                
                except Exception as e:
                    self.issues['low'].append(f"Could not read {req_file}: {e}")
        
        # Try to run safety check if available
        try:
            result = subprocess.run(['safety', 'check'], capture_output=True, text=True, timeout=30)
            if result.returncode != 0 and "No known security vulnerabilities found" not in result.stdout:
                self.issues['high'].append("Safety check found security vulnerabilities in dependencies")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.issues['info'].append("Safety check not available - install with 'pip install safety'")
    
    def validate_configuration_files(self):
        """Validate configuration files for security issues."""
        print("⚙️ Validating Configuration Files...")
        
        config_files = [
            "docker-compose.yml",
            "Dockerfile",
            ".gitignore",
            "nginx.conf",
            "uwsgi.ini"
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        self._check_config_security(config_file, content)
                except Exception as e:
                    self.issues['low'].append(f"Could not read {config_file}: {e}")
        
        # Check .gitignore
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
                
                required_ignores = ['.env', '*.key', '*.pem', 'secrets/', 'config/secrets']
                for ignore_pattern in required_ignores:
                    if ignore_pattern not in gitignore_content:
                        self.issues['medium'].append(f"Missing {ignore_pattern} in .gitignore")
        else:
            self.issues['high'].append("No .gitignore file found - sensitive files may be committed")
    
    def _check_config_security(self, filename: str, content: str):
        """Check configuration file for security issues."""
        if filename == "docker-compose.yml":
            if "privileged: true" in content:
                self.issues['high'].append("Docker container running in privileged mode")
            if "user: root" in content or "user: \"root\"" in content:
                self.issues['medium'].append("Docker container running as root user")
        
        elif filename == "Dockerfile":
            if "USER root" in content and "USER " not in content.split("USER root")[1]:
                self.issues['medium'].append("Dockerfile ends with root user")
            if "ADD http" in content or "ADD https" in content:
                self.issues['low'].append("Dockerfile uses ADD with URL - consider using COPY")
        
        elif filename == "nginx.conf":
            if "server_tokens on" in content:
                self.issues['low'].append("Nginx server tokens enabled - reveals version info")
            if "ssl_protocols" not in content:
                self.issues['medium'].append("SSL protocols not explicitly configured in Nginx")
    
    def print_report(self):
        """Print security validation report."""
        print("\n" + "=" * 60)
        print("🔒 SECURITY VALIDATION REPORT")
        print("=" * 60)
        
        total_issues = sum(len(issues) for issues in self.issues.values())
        
        if total_issues == 0:
            print("✅ No security issues found!")
            return True
        
        severity_colors = {
            'critical': '🚨',
            'high': '🔴',
            'medium': '🟡',
            'low': '🟠',
            'info': 'ℹ️'
        }
        
        has_blocking_issues = False
        
        for severity, issues in self.issues.items():
            if not issues:
                continue
                
            print(f"\n{severity_colors[severity]} {severity.upper()} ({len(issues)} issues):")
            for issue in issues:
                print(f"  - {issue}")
            
            if severity in ['critical', 'high']:
                has_blocking_issues = True
        
        print(f"\n📊 Summary: {total_issues} total issues found")
        
        if has_blocking_issues:
            print("\n❌ VALIDATION FAILED - Critical or high severity issues found")
            print("Please address these issues before deploying to production.")
            return False
        else:
            print("\n✅ VALIDATION PASSED - No blocking security issues")
            return True

def main():
    """Main function to run security validation."""
    validator = SecurityValidator()
    validator.validate_all()
    
    success = validator.print_report()
    
    # Exit with appropriate code for CI/CD
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()