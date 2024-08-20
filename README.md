<!-- <p align="center">
  <a href="" rel="noopener">
 <img src="insert logo here" alt="navsuite logo"></a>
</p> -->

<h3 align="center"><i><b>navsuite</i></b></h3>

<div align="center">

![GitHub Repo stars](https://img.shields.io/github/stars/tannerkoza/navsuite)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)
![GitHub pull requests](https://img.shields.io/github/issues-pr/tannerkoza/navsuite)
![GitHub issues](https://img.shields.io/github/issues/tannerkoza/navsuite)

</div>

---

<p align="center"> A collection of navigation-related Python packages.
    <br> 
</p>

## 📝 Table of Contents

- [Our Mission](#our-mission)
- [Getting Started](#getting-started)
- [Contributing](#contributing)
- [Acknowledgments](#acknowledgement)
  <!-- - [TODO](../TODO.md) -->
  <!-- - [Contributing](../CONTRIBUTING.md) -->

## 🚀 Our Mission <a name = "our-mission"></a>

***navsuite*** was created to provide a centralized repository for Python tools that help facilitate positioning, navigation, and timing (PNT) research and development. This project combines a collection of previously created packages (and any future packages) into one project to allow for easy dependency management and quick feature additions.

- **NOTE:** We are still very early in development as features are being added on an "as-needed" basis. Feel free to request new features in an [issue](https://github.com/tannerkoza/navsuite/issues/new) or refer to the [contributing instructions](/CONTRIBUTING.md) for adding your own features to merge in a [pull request](https://github.com/tannerkoza/navsuite/pulls).

## 🏁 Getting Started <a name = "getting-started"></a>

### Prerequisites

Python **3.10-3.12** are currently supported and tested against using the [`<ubuntu-windows-mac>-latest`](https://docs.github.com/en/actions/using-github-hosted-runners/using-github-hosted-runners/about-github-hosted-runners#supported-runners-and-hardware-resources) operating system runners supported by GitHub Actions.

### Installing ***navsuite*** Packages

Currently, there are no stable releases of any package included in ***navsuite***. Therefore, there are no wheels readily available for download from any package index repository. However, each package can still be installed using the following command prototype:

```sh
pip install "git+https://github.com/tannerkoza/navsuite.git#egg=<package>&subdirectory=src/<package>"
```
In this command, `<package>` can simply be replaced by one of the package names in the `src/` directory (e.g., `navtools`). Additionally, these packages can be installed with any [PEP 517](https://peps.python.org/pep-0517/) compatible build system (in addition to `pip`) and their alternative to the above command.

### Recommendations
- Given the adherence to PEP 517, the editable install command for your respective build system *should* work for each ***navsuite*** package. However, it is recommended to use [rye](https://rye.astral.sh/) in accordance with the [contributing instructions](/CONTRIBUTING.md) for the best editable install experience.
- As always, it is recommended you install these packages to a virtual environment. How that virtual environment is generated is completely up to you.



## ✍️ Contributing <a name = "contributing"></a> 
Feel free to fork and submit [pull requests](https://github.com/tannerkoza/navsuite/pulls) for review after looking at the [contributing instructions](/CONTRIBUTING.md)! If you're interested in becoming a regular contributor, email me at [kozatanner@gmail.com](mailto:kozatanner@gmail.com).

![GitHub contributors](https://img.shields.io/github/contributors/tannerkoza/navsuite)


## 🎉 Acknowledgements <a name = "acknowledgement"></a>
This work is inspired by my time as a student at Auburn University's [GPS & Vehicle Dynamics Laboratory](https://gavlab.auburn.edu/#gsc.tab=0) and all of my fellow lab-mates I met there.
  <!-- - Inspiration -->
  <!-- - References

