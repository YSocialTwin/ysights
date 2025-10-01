# GitHub Actions Workflows

This directory contains GitHub Actions workflows for CI/CD automation.

## Available Workflows

### 1. CI - Code Quality (`ci.yml`)
**Trigger:** Automatic on push/pull request to main/develop branches

Performs code quality checks:
- **Black formatting check**: Ensures code follows Black style
- **Import sorting**: Validates import order with isort
- **Linting**: Checks code with flake8
- **Import test**: Verifies package can be imported

**Matrix:** Python 3.9, 3.10, 3.11, 3.12 on Ubuntu

### 2. Build and Publish to PyPI (`pypi-publish.yml`)
**Trigger:** Manual (workflow_dispatch) or on release

Builds and publishes Python packages to PyPI:
- Builds source distribution and wheel
- Validates package with twine
- Uploads to Test PyPI (manual, optional)
- Publishes to PyPI (on release)

**To manually trigger:**
1. Go to Actions tab
2. Select "Build and Publish to PyPI"
3. Click "Run workflow"
4. Choose whether to publish to Test PyPI

**For releases:** Tag a release on GitHub to automatically publish to PyPI

**Required secrets:**
- Uses trusted publishing (no token needed for main PyPI)
- For Test PyPI, configure in repository settings

### 3. Build and Publish to Conda (`conda-publish.yml`)
**Trigger:** Manual (workflow_dispatch) or on release

Builds conda packages for multiple platforms:
- Builds for Linux, macOS, and Windows
- Python 3.9, 3.10, 3.11, 3.12
- Uploads to Anaconda.org (on request)

**To manually trigger:**
1. Go to Actions tab
2. Select "Build and Publish to Conda"
3. Click "Run workflow"
4. Choose whether to publish to Anaconda

**Required secrets:**
- `ANACONDA_TOKEN`: Token for uploading to Anaconda.org
  - Get token from: https://anaconda.org/settings/access
  - Add to: Repository Settings → Secrets and variables → Actions

## Code Formatting

To format code locally before pushing:

```bash
# Install formatting tools
pip install black isort flake8

# Format code with Black
black ysights/

# Sort imports
isort ysights/

# Check linting
flake8 ysights/
```

## Package Building

### PyPI Package
```bash
pip install build
python -m build
# Output in dist/
```

### Conda Package
```bash
conda install conda-build
conda build conda-recipe/
```

## Configuration Files

- `pyproject.toml`: Python project configuration, Black/isort settings
- `conda-recipe/meta.yaml`: Conda package recipe
- `setup.py`: Legacy setuptools configuration (kept for compatibility)
