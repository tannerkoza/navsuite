import datetime as dt
import pathlib as pl
from dataclasses import dataclass

try:
    import tomllib as tl
except ImportError:
    import tomli as tl

from navtools.io import select_file
from zoneinfo import ZoneInfo


@dataclass
class Constellation:
    reference_constellation: str
    signals: str | list[str]
    mask_angle: float  # [deg]


@dataclass
class MeasurementConfiguration:
    initial_datetime: dt.datetime
    duration: float
    fsim: float

    trajectory_name: str

    constellations: list[Constellation]


def load_configuration(dir: str | pl.Path, sim_type: str):
    """
    Load and preprocess a simulation configuration file based on simulation type.

    Parameters
    ----------
    dir : str or pathlib.Path
        Directory containing the configuration file to load.
    sim_type : str
        Type of simulation to run. Supported types include:
        - "measurement"
        - "correlator" (not yet implemented)
        - "signal" (not yet implemented)

    Returns
    -------
    MeasurementConfiguration
        A structured configuration object for the measurement simulation.

    Raises
    ------
    FileNotFoundError
        If the selected configuration file cannot be found.
    toml.TomlDecodeError
        If the configuration file is not valid TOML.
    ValueError
        If the `sim_type` is not one of the supported types.
    """
    selected_config = select_file(directory=dir, title="navsim")

    with open(selected_config, "rb") as config_file:
        config = tl.load(config_file)

        match sim_type.casefold():
            case "measurement":
                preprocessed_config = _preprocess_measurement_config(config=config)
                loaded_config = MeasurementConfiguration(**preprocessed_config)

            case "correlator":  # TODO: implement correlator simulation preprocessing
                pass

            case "signal":  # TODO: implement signal simulation preprocessing
                pass

        return loaded_config


def _preprocess_measurement_config(config: dict):
    initial_datetime = config.pop("initial_datetime")
    constellations = config.pop("constellation")

    # casefold configuration keys if need be
    new_config = {key.casefold(): value for key, value in config.items()}

    if not initial_datetime.tzinfo == dt.timezone.utc:
        initial_datetime = initial_datetime.astimezone(ZoneInfo("UTC"))

    new_config["initial_datetime"] = initial_datetime
    new_config["constellations"] = [
        Constellation(**constellation) for constellation in constellations
    ]

    return new_config
