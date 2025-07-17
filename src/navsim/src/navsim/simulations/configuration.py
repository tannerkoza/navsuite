import datetime as dt
import pathlib as pl
from dataclasses import dataclass, fields, MISSING

try:
    import tomllib as tl
except ImportError:
    import tomli as tl

from navtools.io import select_file
from zoneinfo import ZoneInfo


@dataclass
class Constellation:
    reference_constellation: str
    signals: list[str]
    mask_angle: float  # [deg]
    sv_clock_type: str | None = None


@dataclass
class MeasurementConfiguration:
    constellation: list[Constellation]
    rx_clock_type: str
    ionosphere: bool
    troposphere: bool


@dataclass
class GeneralConfiguration:
    initial_datetime: dt.datetime
    duration: float
    fsim: float
    trajectory_name: str


@dataclass
class NavsimConfiguration:
    general: GeneralConfiguration
    measurement: MeasurementConfiguration


def load_configuration(dir: str | pl.Path):
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

        preprocessed_config = _preprocess_config(config=config)
        loaded_config = _dict_to_dataclass(
            cls=NavsimConfiguration, data=preprocessed_config
        )

        return loaded_config


def _preprocess_config(config: dict):
    new_config = {}

    # general
    general = _dict_to_dataclass(cls=GeneralConfiguration, data=config)

    if not general.initial_datetime.tzinfo == dt.timezone.utc:
        general.initial_datetime = general.initial_datetime.astimezone(ZoneInfo("UTC"))

    new_config["general"] = general

    # measurement
    measurement = _dict_to_dataclass(cls=MeasurementConfiguration, data=config)
    measurement.constellation = [
        _dict_to_dataclass(cls=Constellation, data=constellation)
        for constellation in measurement.constellation
    ]
    new_config["measurement"] = measurement

    return new_config


from typing import Dict, Any, Type, TypeVar

T = TypeVar("T")


def _dict_to_dataclass(cls: Type[T], data: Dict[str, Any]) -> T:
    """Convert dict to dataclass with error handling"""
    class_fields = {f.name: f for f in fields(cls)}

    # Check for missing required fields
    required_fields = {
        name
        for name, field in class_fields.items()
        if field.default is field.default_factory is MISSING
    }

    missing_fields = required_fields - set(data.keys())
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    # Filter to only valid fields
    filtered_data = {k: v for k, v in data.items() if k in class_fields}

    return cls(**filtered_data)
