<!-- <p align="center">
  <a href="" rel="noopener">
 <img src="insert logo here" alt="navsuite logo"></a>
</p> -->

<h3 align="center"><i><b>navsim</i></b></h3>

<div align="center">

![GitHub Repo stars](https://img.shields.io/github/stars/tannerkoza/navsuite)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)
![GitHub pull requests](https://img.shields.io/github/issues-pr/tannerkoza/navsuite/navsim)
![GitHub issues](https://img.shields.io/github/issues/tannerkoza/navsuite/navsim)

</div>

---

<p align="center"> A Python satellite navigation simulator package within the navsuite collection of navigation-related tools.
    <br>
</p>

## 🚀 Overview <a name = "overview"></a>

**_navsim_** is part of **navsuite**, a centralized repository for Python tools that facilitate positioning, navigation, and timing (PNT) research and development. **_navsim_** provides versatile simulation tools specifically designed for satellite navigation research, combining both library functionality and executable capabilities.

## Features

- **Dual Usage Modes**: Use as both a Python library package and standalone executable
  - All simulation modules can be imported and used as any other library package (e.g., clock simulation, satellite simulation, satellite measurement simulation, etc.)
  - Satellite measurement simulation can be configured and run end-to-end to generate [ASPN](https://www.aspn.us/) measurements in an [LCM](https://lcm-proj.github.io/lcm/) log file
- **Error Simulation**: Provides ability to simulate satellite measurements at a broader scale, while also allowing for simulation of their corresponding errors (e.g., clock, ionosphere, troposphere, etc.) outside of the context of a measurement simulation

## 🏁 Getting Started <a name = "getting-started"></a>

### Prerequisites

Python **3.10-3.12** are currently supported and tested against using the [`<ubuntu-windows-mac>-latest`](https://docs.github.com/en/actions/using-github-hosted-runners/using-github-hosted-runners/about-github-hosted-runners#supported-runners-and-hardware-resources) operating system runners supported by GitHub Actions.

### Installation

### As a Library Package

navsim can be installed directly from the navsuite repository:

```bash
# Install navsim package from navsuite
pip install "navsim @ git+https://github.com/tannerkoza/navsuite.git#subdirectory=src/navsim"
```

### Development Installation

For development work, use an editable install. The project recommends using [uv](https://docs.astral.sh/uv/) for the best experience. The process for doing so is explained in the [contributing instructions](/CONTRIBUTING.md).

## Usage

### As a Library Package

Import and use navsim in your Python projects:

```python
import navsim
from pathlib import Path

# run a simulation programmatically (like the executable)
navsim.simulate()

# with custom configuration and log directories
navsim.simulate(
    config_dir=Path("my_configs"),
    log_dir=Path("my_logs")
)

# use error functions and other available classes
from navsim.clock import NavigationClock, compute_clock_states

clock = NavigationClock(h0=2e-21, h1=1e-22, h2=2e-20)

clock_bias, clock_drift = compute_clock_states(
            h0=clock.h0,
            h2=clock.h2,
            T=0.001,
            nperiods=100,
        ) # [m], [m/s]
```

### As an Executable Application

navsim can be executed as a standalone application from the command line to run complete satellite navigation simulations:

```bash
# run navsim as an executable (basic usage)
navsim

# with custom configuration directory
navsim --config-dir /path/to/config

# with custom log output directory
navsim --log-dir /path/to/logs

# with both custom directories
navsim --config-dir /path/to/config --log-dir /path/to/logs

```

#### Command-Line Options

- `--config-dir`: Directory containing configuration files (optional)
  - If not specified, uses the package default configuration path
- `--log-dir`: Directory to write log files (optional)
  - **Linux/macOS**: `~/.navsim/logs/` (default)
  - **Windows**: `C:\Users\<user>\.navsim\logs\` (default)

#### Simulation Output

The executable generates:

- **LCM log files**: Timestamped simulation results in LCM format
- **Naming convention**: `YYYY-MM-DD_HH:MM:SSZ_<config_name>.log`
- **Location**: Specified log directory or platform default

## Development Status

🚧 **Early Development**: navsim is in active development with features being added on an "as-needed" basis.

### Current State

- No stable releases yet
- Pre-release development phase
- Cross-platform testing (Ubuntu, Windows, macOS)
- PEP 517 compliant build system

## ✍️ Contributing <a name = "contributing"></a>

navsim welcomes contributions as part of the navsuite project. Feel free to fork and submit [pull requests](https://github.com/tannerkoza/navsuite/pulls) for review after looking at the [contributing instructions](/CONTRIBUTING.md)! If you're interested in becoming a regular contributor, email me at [kozatanner@gmail.com](mailto:kozatanner@gmail.com).

![GitHub contributors](https://img.shields.io/github/contributors/tannerkoza/navsuite)

### Getting Started

1. Read the [contributing instructions](/CONTRIBUTING.md)
2. Fork the navsuite repository
3. Follow the recommended development setup with `uv`

### Requesting Features

Submit feature requests as [GitHub Issues](https://github.com/tannerkoza/navsuite/issues/new). Features are added based on research and development needs.

### Pull Requests

1. Fork the repository
2. Create a feature branch
3. Follow the contribution guidelines
4. Submit a [pull request](https://github.com/tannerkoza/navsuite/pulls) for review

### Becoming a Regular Contributor

Interested in regular contribution? Email kozatanner@gmail.com to discuss collaboration opportunities.

## Acknowledgments

This work is inspired by research conducted at Auburn University's [GPS & Vehicle Dynamics Laboratory](https://gavlab.auburn.edu/#gsc.tab=0) and the collaborative efforts of fellow researchers in the navigation community.

navsim is developed as part of the broader mission to advance positioning, navigation, and timing research through accessible Python tools.

---

**Note**: navsim is in early development as part of the navsuite project. APIs and features may change as development progresses toward stable releases.
