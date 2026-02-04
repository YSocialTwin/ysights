# ySights Documentation

This directory contains the Sphinx documentation for ySights.

## Building the Documentation

### Local Build

To build the documentation locally:

```bash
cd docs
make html
```

The generated HTML will be in `build/html/`. Open `build/html/index.html` in your browser to view.

### Clean Build

To clean previous builds and rebuild:

```bash
cd docs
make clean
make html
```

## Documentation Structure

- `source/`: Source files for the documentation
  - `conf.py`: Sphinx configuration
  - `index.rst`: Main documentation page
  - `modules/`: API reference documentation
- `build/`: Generated documentation (not committed to git)
- `VISIBILITY_PARADOX.md`: Detailed mathematical formulation and theoretical background for the visibility paradox algorithm

## ReadTheDocs

This documentation is configured for ReadTheDocs. The `.readthedocs.yaml` file in the repository root
configures the build environment.

## Requirements

The documentation build requires:
- sphinx
- sphinx-rtd-theme
- sphinx-autodoc-typehints

These are automatically installed by ReadTheDocs using the configuration file.
