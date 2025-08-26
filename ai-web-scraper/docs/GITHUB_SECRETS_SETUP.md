# GitHub Secrets Setup Guide

This guide explains how to securely configure GitHub Secrets for CI/CD pipelines.

## Required Secrets

### Test Environment Secrets

Set these secrets in your GitHub repository settings:

1. **TEST_DATABASE_URL**
   ```
   postgresql://test_user:secure_test_password@localhost:5432/test_webscraper
   ```

2. **TEST_REDIS_URL**
   ```
   redis://localhost:6379/0
   ```

3. **TEST_GEMINI_API_KEY**
   ```
   test-api-key-for-ci-cd-only
   ```

## Setting Up GitHub Secrets

### Via GitHub Web Interface

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the name and value

### Via GitHub CLI

```bash
# Set test database URL
gh secret set TEST_DATABASE_URL --body "postgresql://test_user:$(openssl rand -hex 16)@localhost:5432/test_webscraper"

# Set test Redis URL
gh secret set TEST_REDIS_URL --body "redis://localhost:6379/0"

# Set test API key
gh secret set TEST_GEMINI_API_KEY --body "test-api-key-$(openssl rand -hex 16)"
```

## Security Best Practices

### ✅ Do's
- Use unique credentials for each environment (dev/test/prod)
- Generate random passwords for test databases
- Use descriptive secret names with environment prefixes
- Rotate secrets regularly
- Use least-privilege access for test credentials

### ❌ Don'ts
- Never use production credentials in CI/CD
- Don't hardcode secrets in workflow files
- Don't use the same password across environments
- Don't commit secrets to version control
- Don't use weak or predictable test passwords

## Environment-Specific Secrets

### Development
```bash
DEV_DATABASE_URL=postgresql://dev_user:dev_password@dev-db:5432/webscraper_dev
DEV_REDIS_URL=redis://dev-redis:6379/0
DEV_GEMINI_API_KEY=dev-api-key
```

### Staging
```bash
STAGING_DATABASE_URL=postgresql://staging_user:staging_password@staging-db:5432/webscraper_staging
STAGING_REDIS_URL=redis://staging-redis:6379/0
STAGING_GEMINI_API_KEY=staging-api-key
```

### Production
```bash
PROD_DATABASE_URL=postgresql://prod_user:prod_password@prod-db:5432/webscraper_prod
PROD_REDIS_URL=redis://prod-redis:6379/0
PROD_GEMINI_API_KEY=prod-api-key
```

## Validation Script

Create a script to validate that all required secrets are set:

```bash
#!/bin/bash
# validate-secrets.sh

required_secrets=(
    "TEST_DATABASE_URL"
    "TEST_REDIS_URL"
    "TEST_GEMINI_API_KEY"
)

echo "Validating GitHub Secrets..."

for secret in "${required_secrets[@]}"; do
    if gh secret list | grep -q "$secret"; then
        echo "✅ $secret is set"
    else
        echo "❌ $secret is missing"
        exit 1
    fi
done

echo "✅ All required secrets are configured"
```

## Troubleshooting

### Common Issues

1. **Secret not found in workflow**
   - Check secret name spelling
   - Ensure secret is set at repository level
   - Verify workflow has access to secrets

2. **Invalid credentials in tests**
   - Ensure test database is running
   - Check connection parameters
   - Verify credentials are correct

3. **API key validation fails**
   - Use a valid test API key
   - Check API key format
   - Ensure API key has necessary permissions

### Debug Commands

```bash
# List all secrets (names only, values are hidden)
gh secret list

# Delete a secret
gh secret delete SECRET_NAME

# Update a secret
gh secret set SECRET_NAME --body "new_value"
```

## Security Monitoring

Monitor your secrets usage:

1. Check GitHub Actions logs for authentication failures
2. Monitor for unexpected secret access patterns
3. Set up alerts for failed CI/CD runs
4. Regularly audit secret usage and rotate credentials

## Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Security Hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [Managing encrypted secrets for your repository](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository)