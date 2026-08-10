# PyPI Publishing Setup Guide

This document provides step-by-step instructions for setting up PyPI publishing for the ysights package using API token authentication.

## Overview

The repository uses GitHub Actions to automatically publish packages to PyPI. The workflow has been configured to use API token authentication instead of OIDC trusted publishing for better compatibility and control.

## Prerequisites

- A PyPI account (https://pypi.org)
- Repository maintainer/admin access to configure GitHub secrets
- Two-factor authentication enabled on your PyPI account (required by PyPI)

## Setup Steps

### 1. Create PyPI Account

If you don't already have a PyPI account:

1. Go to https://pypi.org/account/register/
2. Fill in your details and create an account
3. Verify your email address

### 2. Enable Two-Factor Authentication (Required)

PyPI requires 2FA for all accounts that publish packages:

1. Log in to your PyPI account
2. Go to Account Settings: https://pypi.org/manage/account/
3. Navigate to "Account security" → "Two-factor authentication"
4. Follow the instructions to set up 2FA using an authenticator app

### 3. Generate PyPI API Token

API tokens are more secure than passwords and can be scoped to specific projects:

1. Log in to PyPI: https://pypi.org
2. Go to Account Settings → API tokens: https://pypi.org/manage/account/token/
3. Click "Add API token"
4. Fill in the token details:
   - **Token name**: `GitHub Actions - ysights` (or any descriptive name)
   - **Scope**: 
     - For first-time setup: Choose "Entire account"
     - After first successful upload: You can create a project-specific token for better security
5. Click "Add token"
6. **IMPORTANT**: Copy the token immediately! It starts with `pypi-` and will only be shown once.
   - Example format: `pypi-AgEIcHlwaS5vcmcC...` (much longer)

### 4. Add Token to GitHub Repository Secrets

1. Go to your GitHub repository
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click "New repository secret"
4. Add the main PyPI token:
   - **Name**: `PYPI_API_TOKEN`
   - **Secret**: Paste the entire token (including the `pypi-` prefix)
   - Click "Add secret"

### 5. (Optional) Set Up Test PyPI

Test PyPI is a separate instance for testing package uploads before publishing to the main PyPI:

1. Create an account at https://test.pypi.org/account/register/
2. Enable 2FA on Test PyPI (separate from main PyPI)
3. Generate a Test PyPI API token:
   - Go to https://test.pypi.org/manage/account/token/
   - Create a token with scope "Entire account"
   - Copy the token (starts with `pypi-`)
4. Add to GitHub secrets:
   - Name: `TEST_PYPI_API_TOKEN`
   - Secret: Paste the Test PyPI token

## How to Use

### Manual Testing (Test PyPI)

To test the package publishing without affecting the main PyPI:

1. Go to the **Actions** tab in your GitHub repository
2. Select "Build and Publish to PyPI" workflow
3. Click "Run workflow"
4. Select branch (usually `main`)
5. Set "Publish to PyPI" to `true`
6. Click "Run workflow"

**Note:** When triggered manually with "Publish to PyPI" set to `true`, the workflow publishes to **Test PyPI** (not production PyPI) using the `TEST_PYPI_API_TOKEN`. This allows you to test the publishing process safely.

### Automatic Publishing (Main PyPI)

Publishing to main PyPI happens automatically when you create a release:

1. Go to your repository on GitHub
2. Click on "Releases" → "Create a new release"
3. Choose or create a tag (e.g., `v0.2.0`)
4. Fill in release title and description
5. Click "Publish release"

The GitHub Action will automatically:
- Build the package (source distribution and wheel)
- Run quality checks with twine
- Upload to PyPI using the `PYPI_API_TOKEN`

## Workflow Details

The workflow file is located at `.github/workflows/pypi-publish.yml` and performs these steps:

1. **Checkout code**: Gets the latest code from the repository
2. **Set up Python**: Installs Python 3.11
3. **Install build tools**: Installs `build`, `twine`, and `wheel`
4. **Build package**: Creates source distribution (`.tar.gz`) and wheel (`.whl`)
5. **Check package**: Validates the package with `twine check`
6. **Upload artifacts**: Stores built packages as GitHub artifacts
7. **Publish**: Uploads to PyPI or Test PyPI using twine

### Authentication Method

The workflow uses token-based authentication via environment variables:
```yaml
env:
  TWINE_USERNAME: __token__
  TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

- `TWINE_USERNAME` is always `__token__` when using API tokens
- `TWINE_PASSWORD` contains the actual API token from GitHub secrets

## Troubleshooting

### Token Not Working

- Ensure the token includes the `pypi-` prefix
- Verify 2FA is enabled on your PyPI account
- Check that the token hasn't been revoked
- For project-specific tokens, ensure the project name matches exactly

### Package Already Exists

If you see "File already exists" errors:
- The workflow uses `--skip-existing` to avoid errors
- You cannot re-upload the same version; increment the version number in `pyproject.toml` and `setup.py`

### Workflow Permission Errors

- Ensure the token is added as a repository secret (not environment secret)
- Verify the secret name matches exactly: `PYPI_API_TOKEN` (case-sensitive)

### Build Failures

- Check that all required files are included in the repository
- Verify `pyproject.toml` and `setup.py` are properly configured
- Review the GitHub Actions logs for specific error messages

## Security Best Practices

1. **Never commit tokens**: API tokens should only be stored in GitHub secrets
2. **Use project-specific tokens**: After first upload, create a project-scoped token
3. **Rotate tokens regularly**: Generate new tokens periodically
4. **Revoke unused tokens**: Delete tokens that are no longer needed
5. **Monitor uploads**: Check PyPI for any unexpected package uploads

## Updating Package Version

Before publishing a new version:

1. Update version in `pyproject.toml` (primary source):
   ```toml
   version = "0.2.0"
   ```

2. Update version in `setup.py` (for backward compatibility):
   ```python
   version="0.2.0",
   ```
   
   **Note:** This project maintains both `pyproject.toml` (modern, PEP 621 standard) and `setup.py` (legacy) for compatibility. The `pyproject.toml` is the primary source of truth for the version. If your project only uses `pyproject.toml`, you can skip updating `setup.py`.

3. Commit the version changes
4. Create a new release with the corresponding tag (e.g., `v0.2.0`)

## Migration from OIDC

This repository has been migrated from OIDC trusted publishing to API token authentication. The changes include:

- **Removed**: `id-token: write` permission from workflow
- **Removed**: `pypa/gh-action-pypi-publish` GitHub Action
- **Added**: Direct `twine upload` commands with token authentication
- **Added**: Environment variables for `TWINE_USERNAME` and `TWINE_PASSWORD`

Benefits of this approach:
- More explicit control over authentication
- Works with all PyPI-compatible repositories
- Easier to debug upload issues
- No dependency on GitHub's OIDC infrastructure

## References

- PyPI API Token Documentation: https://pypi.org/help/#apitoken
- Twine Documentation: https://twine.readthedocs.io/
- GitHub Actions Secrets: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- Python Packaging Guide: https://packaging.python.org/
