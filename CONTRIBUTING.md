# NavSuite Development Setup with UV

This guide walks you through setting up the NavSuite monorepo for development using UV, a fast Python package manager. NavSuite is a collection of navigation-related Python packages designed for positioning, navigation, and timing (PNT) research and development.

## Prerequisites

- Python 3.10-3.12 (currently supported versions)
- [UV package manager](https://docs.astral.sh/uv/) installed on your system

### Installing UV

If you haven't installed UV yet, you can install it using:

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: Install via pip
pip install uv
```

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/tannerkoza/navsuite.git
cd navsuite
```

### 2. Initialize the Development Environment

NavSuite uses a monorepo structure with packages located in the `src/` directory. Use UV to set up the development environment:

```bash
# Initialize a virtual environment and sync dependencies
uv sync
```

This command will:
- Create a virtual environment if one doesn't exist
- Install all dependencies for the workspace
- Set up editable installs for all packages in the monorepo

### 3. Verify Installation

Check that the environment is properly set up:

```bash
# Activate the virtual environment (if needed)
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate     # On Windows

# List installed packages
uv pip list
```

## Working with Individual Packages

### Installing Specific Package Dependencies

If you're working on a specific package within the monorepo, you can sync dependencies for that package:

```bash
# Sync all packages (recommended for development)
uv sync --all-packages

# Or work with a specific package
uv sync --package <package-name>
```

Replace `<package-name>` with one of the package names from the `src/` directory (e.g., `navtools`).

### Adding New Dependencies

To add dependencies to a specific package:

```bash
# Navigate to the package directory
cd src/<package-name>

# Add a dependency
uv add <dependency-name>

# Add a development dependency
uv add --dev <dependency-name>

# Add an optional dependency group
uv add --optional <group-name> <dependency-name>
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

Edit the code in the relevant package under `src/<package-name>/`.

### 3. Sync Dependencies After Changes

If you've modified `pyproject.toml` files or added new dependencies:

```bash
uv sync
```

## Managing the Monorepo

### Working with Multiple Packages

When working with interdependent packages within the monorepo:

```bash
# Sync all packages and their cross-dependencies
uv sync --all-packages

# This ensures that changes in one package are reflected in dependent packages
```

### Dependency Updates

Keep dependencies up to date:

```bash
# Update all dependencies
uv sync --upgrade

# Update specific dependency
uv add <package-name> --upgrade
```

## Tips for Contributing

### 1. Environment Isolation

UV automatically creates isolated environments, but you can also create project-specific environments:

```bash
# Create a new virtual environment for the project
uv venv

# Activate it
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

### 2. Cross-Package Development

When developing features that span multiple packages:

1. Make sure all packages are synced: `uv sync --all-packages`
2. Test changes across packages to ensure compatibility
3. Update version dependencies in `pyproject.toml` files as needed

## Troubleshooting

### Common Issues

**Dependency conflicts:**
```bash
# Clear the lock file and re-sync
rm uv.lock
uv sync
```

**Package not found:**
```bash
# Ensure you're in the correct directory
pwd
# Should be in the navsuite root directory

# Verify package structure
ls src/
```

**Virtual environment issues:**
```bash
# Remove and recreate the virtual environment
rm -rf .venv
uv sync
```

### Getting Help

- Check the [navsuite issues](https://github.com/tannerkoza/navsuite/issues) for known problems
- Refer to the [UV documentation](https://docs.astral.sh/uv/) for UV-specific questions
- Review the contributing guidelines in the repository

## Summary Commands

Here are the most commonly used commands for NavSuite development:

```bash
# Initial setup
git clone https://github.com/tannerkoza/navsuite.git
cd navsuite
uv sync

# Development workflow
uv sync --all-packages          # Sync all packages
uv add <dependency>             # Add new dependency
uv run pytest                  # Run tests
uv build                       # Build packages

# Maintenance
uv sync --upgrade              # Update dependencies
uv tree                        # Show dependency tree
uv pip list                    # List installed packages
```

This setup provides a robust development environment for contributing to any of the packages in the NavSuite monorepo while maintaining proper dependency isolation and management.