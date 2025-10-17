# Repository Setup Guide

This guide documents the repository configuration settings required for the GitHub Actions workflows to function properly. These workflows enable automated publishing of packages to PyPI and Conda, as well as documentation deployment to GitHub Pages.

## Table of Contents

1. [PyPI Package Publishing Setup](#pypi-package-publishing-setup)
2. [Conda Package Publishing Setup](#conda-package-publishing-setup)
3. [GitHub Pages Documentation Setup](#github-pages-documentation-setup)
4. [Verifying Your Setup](#verifying-your-setup)

---

## PyPI Package Publishing Setup

The PyPI publishing workflow (`.github/workflows/pypi-publish.yml`) uses **Trusted Publishing** (OpenID Connect), which is the recommended secure method for publishing to PyPI without using API tokens.

### Required Steps

#### 1. Configure PyPI Trusted Publisher

1. **Log in to PyPI** at https://pypi.org (or https://test.pypi.org for TestPyPI)

2. **Navigate to Publishing Settings**:
   - Go to your account settings
   - Click on "Publishing" in the left sidebar
   - Or go directly to: https://pypi.org/manage/account/publishing/

3. **Add a new pending publisher** (if the package doesn't exist yet):
   - Click "Add a new pending publisher"
   - Fill in the following details:
     - **PyPI Project Name**: `ysights`
     - **Owner**: `YSocialTwin`
     - **Repository name**: `ysights`
     - **Workflow name**: `pypi-publish.yml`
     - **Environment name**: (leave blank)
   - Click "Add"

4. **Configure trusted publisher** (if the package already exists):
   - Go to your project page: https://pypi.org/project/ysights/
   - Click "Manage" → "Publishing"
   - Click "Add a new publisher"
   - Fill in the same details as above

#### 2. Verify Workflow Permissions

The workflow already has the required permissions configured:

```yaml
permissions:
  id-token: write  # Required for trusted publishing
  contents: read
```

### How It Works

- **Manual Trigger**: You can manually trigger the workflow from the Actions tab, which publishes to **Test PyPI**
- **Automatic Publishing**: When you create a GitHub Release, the package is automatically published to **PyPI**

### No Secrets Required!

With Trusted Publishing, you don't need to create or manage PyPI API tokens in GitHub Secrets. The authentication happens automatically via OpenID Connect.

---

## Conda Package Publishing Setup

The Conda publishing workflow (`.github/workflows/conda-publish.yml`) requires an Anaconda authentication token to upload packages to Anaconda.org (conda-forge or your channel).

### Required Steps

#### 1. Create an Anaconda Account

If you don't have one already:
- Go to https://anaconda.org
- Create an account or log in

#### 2. Generate an API Token

1. **Log in to Anaconda.org**

2. **Go to Settings**:
   - Click on your username in the top right
   - Select "Settings" from the dropdown
   - Or go directly to: https://anaconda.org/YOUR_USERNAME/settings/access

3. **Create a new token**:
   - Click "Create new token" or "Generate Token"
   - Give it a descriptive name (e.g., "ysights-github-actions")
   - Set appropriate scopes:
     - ✅ `api:read` - Read access to API
     - ✅ `api:write` - Write access to API (required for uploading)
   - Click "Create" and **save the token securely** (it won't be shown again)

#### 3. Add Token to GitHub Secrets

1. **Go to your repository** on GitHub: https://github.com/YSocialTwin/ysights

2. **Navigate to Settings**:
   - Click "Settings" tab
   - In the left sidebar, click "Secrets and variables" → "Actions"

3. **Add the secret**:
   - Click "New repository secret"
   - **Name**: `ANACONDA_TOKEN`
   - **Value**: Paste the token you generated from Anaconda.org
   - Click "Add secret"

#### 4. Verify Channel Configuration

Make sure you have a channel on Anaconda.org where packages will be uploaded:
- Your default channel is typically: `https://anaconda.org/YOUR_USERNAME`
- Or set up a conda-forge feedstock (more advanced)

### How It Works

- **Manual Trigger**: You can manually trigger the workflow from the Actions tab to build and optionally publish packages
- **Automatic Publishing**: When you create a GitHub Release, packages are automatically built and published
- The workflow builds packages for multiple platforms (Linux, macOS, Windows) and Python versions (3.9-3.12)

---

## GitHub Pages Documentation Setup

The documentation workflow (`.github/workflows/docs.yml`) builds Sphinx documentation and publishes it to GitHub Pages.

### Required Steps

#### 1. Enable GitHub Pages

1. **Go to your repository** on GitHub: https://github.com/YSocialTwin/ysights

2. **Navigate to Settings**:
   - Click "Settings" tab
   - In the left sidebar, scroll down to "Pages"

3. **Configure GitHub Pages**:
   - Under "Build and deployment":
     - **Source**: Select "GitHub Actions"
     - (Not "Deploy from a branch" - the workflow handles deployment)
   - Click "Save" if needed

#### 2. Verify Workflow Permissions

The workflow already has the required permissions configured:

```yaml
permissions:
  contents: read
  pages: write      # Required to deploy to GitHub Pages
  id-token: write   # Required for GitHub Pages deployment
```

#### 3. Set Up Custom Domain (Optional)

If you want to use a custom domain:

1. In the GitHub Pages settings (same page as above)
2. Under "Custom domain", enter your domain (e.g., `docs.ysights.com`)
3. Follow GitHub's instructions for DNS configuration
4. Wait for DNS verification and HTTPS certificate provisioning

### How It Works

- **Automatic Builds**: Documentation is built on every push to `main` or `develop` branches (to verify it builds)
- **Automatic Publishing**: Documentation is published to GitHub Pages on pushes to `main` branch
- **Manual Trigger**: You can manually trigger the workflow with an option to publish immediately
- **Pull Requests**: Documentation is built (but not published) on PRs to verify changes

### Accessing Your Documentation

Once published, your documentation will be available at:
- **Default URL**: `https://ysocialtwin.github.io/ysights/`
  - Note: GitHub Pages URLs use lowercase organization names
- **Custom Domain**: If configured, your custom domain

### Environment Configuration (Already Set Up)

The workflow uses a GitHub Pages environment which provides:
- Deployment protection rules (optional)
- Deployment history and rollback capabilities
- URL information in deployment status

The environment is automatically created by the workflow with:
```yaml
environment:
  name: github-pages
  url: ${{ steps.deployment.outputs.page_url }}
```

---

## Verifying Your Setup

### Test PyPI Publishing

1. Go to the "Actions" tab in your repository
2. Select "Build and Publish to PyPI" workflow
3. Click "Run workflow"
4. Select the branch (e.g., `main`)
5. Choose `publish: true` from the dropdown
6. Click "Run workflow"
7. Monitor the workflow execution
8. Check Test PyPI for your package: https://test.pypi.org/project/ysights/

### Test Conda Publishing

1. Go to the "Actions" tab in your repository
2. Select "Build and Publish to Conda" workflow
3. Click "Run workflow"
4. Select the branch (e.g., `main`)
5. Choose `publish: true` from the dropdown
6. Click "Run workflow"
7. Monitor the workflow execution (note: builds for multiple platforms)
8. Check your Anaconda.org channel for the package

### Test Documentation Publishing

1. Go to the "Actions" tab in your repository
2. Select "Documentation" workflow
3. Click "Run workflow"
4. Select the branch (e.g., `main`)
5. Check the box for "Publish documentation to GitHub Pages"
6. Click "Run workflow"
7. Monitor the workflow execution
8. Visit your GitHub Pages URL to see the documentation

### Automatic Publishing via Releases

The easiest way to publish everything is to create a GitHub Release:

1. Go to the "Releases" section of your repository
2. Click "Draft a new release"
3. Create a new tag (e.g., `v0.1.0`)
4. Fill in the release title and description
5. Click "Publish release"

This will automatically trigger:
- PyPI package publishing
- Conda package publishing
- Documentation update (if on main branch)

---

## Troubleshooting

### PyPI Publishing Issues

**Problem**: "Trusted publishing exchange failure"
- **Solution**: Verify that the PyPI trusted publisher is configured with the exact values:
  - Owner: `YSocialTwin`
  - Repository: `ysights`
  - Workflow: `pypi-publish.yml`

**Problem**: "Package name already exists"
- **Solution**: If someone else has claimed the package name, you'll need to choose a different name or contact PyPI support.

### Conda Publishing Issues

**Problem**: "ANACONDA_TOKEN not set"
- **Solution**: Verify the secret is named exactly `ANACONDA_TOKEN` (case-sensitive) in GitHub repository secrets.

**Problem**: "Upload failed: Unauthorized"
- **Solution**: Regenerate the Anaconda token with the correct scopes (`api:write`).

### GitHub Pages Issues

**Problem**: "Pages deployment failed"
- **Solution**: Verify that GitHub Pages is set to "GitHub Actions" as the source (not "Deploy from a branch").

**Problem**: "404 after deployment"
- **Solution**: It may take a few minutes for the first deployment. Check the Actions logs for errors.

---

## Security Best Practices

1. **Never commit secrets to the repository**
   - Use GitHub Secrets for sensitive tokens
   - Use Trusted Publishing when possible (PyPI)

2. **Regularly rotate tokens**
   - Update Anaconda tokens periodically
   - Revoke old tokens after rotation

3. **Use minimal permissions**
   - Grant only necessary scopes to tokens
   - Use workflow-level permissions restrictions

4. **Monitor workflow runs**
   - Review Actions logs for suspicious activity
   - Set up notifications for failed workflows

5. **Protect sensitive branches**
   - Require pull request reviews for `main` branch
   - Use branch protection rules

---

## Additional Resources

- **PyPI Trusted Publishing**: https://docs.pypi.org/trusted-publishers/
- **GitHub Actions OIDC**: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect
- **Anaconda Upload**: https://docs.anaconda.com/anaconda/user-guide/tasks/work-with-packages/#uploading-packages
- **GitHub Pages**: https://docs.github.com/en/pages
- **GitHub Actions Secrets**: https://docs.github.com/en/actions/security-guides/encrypted-secrets

---

## Questions or Issues?

If you encounter problems with the setup:

1. Check the workflow logs in the Actions tab for detailed error messages
2. Review this guide to ensure all steps were followed
3. Open an issue in the repository with details about the problem
4. Contact the repository maintainers

---

*Last updated: October 2024*
