import pathlib as pl

PROJECT_PATH = pl.Path(__file__).parents[2]
PACKAGE_PATH = pl.Path(__file__).parent
CONFIG_PATH = PACKAGE_PATH / "config"
LOG_PATH = pl.Path.home() / ".navsim" / "logs"
