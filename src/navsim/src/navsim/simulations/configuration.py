import datetime as dt
import pathlib as pl
from dataclasses import MISSING, dataclass, fields

try:
    import tomllib as tl
except ImportError:
    import tomli as tl

from typing import Any, Dict, Type, TypeVar

from navtools.io import select_file
from zoneinfo import ZoneInfo


@dataclass
class Constellation:
    """
    Configuration for a satellite constellation used in simulation.

    This dataclass holds all parameters necessary to configure a satellite
    constellation for navigation simulation, including signal types, masking
    angles, and power characteristics.

    Attributes
    ----------
    reference_constellation : str
        The name of the reference constellation (e.g., 'GPS', 'Galileo', 'GLONASS').
    signals : list of str
        List of signal identifiers for the constellation (e.g., ['GPS_L1C', 'GPS_L2C']).
    mask_angle : float
        Elevation mask angle in degrees below which satellites are ignored.
        Satellites below this angle are not used in positioning calculations.
    transmit_eirp : float, optional
        Effective Isotropic Radiated Power in dBW. Default is 29.5 dBW,
        which is a reasonable value for GNSS signals.
    cn0_attenuation : float, optional
        Carrier-to-noise density ratio attenuation in dB. Default is 0.0 dB
        (no attenuation).

    Examples
    --------
    >>> gps_config = Constellation(
    ...     reference_constellation='GPS',
    ...     signals=['L1C', 'L2C'],
    ...     mask_angle=10.0,
    ...     transmit_eirp=28.0,
    ...     cn0_attenuation=2.0
    ... )
    """

    reference_constellation: str
    signals: list[str]
    mask_angle: float  # [deg]
    transmit_eirp: float = 29.5  # [dBW] - default is reasonable GNSS value
    cn0_attenuation: float = 0.0  # [dB]


@dataclass
class MeasurementConfiguration:
    """
    Measurement simulation settings and parameters.

    This dataclass contains all configuration parameters related to measurement
    simulation, including constellation setups, receiver characteristics,
    and atmospheric modeling options.

    Attributes
    ----------
    constellation : list of Constellation
        List of constellation configurations to include in the simulation.
        Each constellation defines its own signals and parameters.
    rx_clock_type : str
        Receiver clock type model (e.g., 'ocxo', 'rubidium', 'cesium').
        Determines the clock error characteristics for the receiver.
    rx_noise : bool
        Defines whether or not measurement noise is generated and applied.
    ionosphere : bool
        Whether to model ionospheric delay effects in the simulation.
        If True, ionospheric corrections will be applied to measurements.
    troposphere : bool
        Whether to model tropospheric delay effects in the simulation.
        If True, tropospheric corrections will be applied to measurements.
    pseudorange_awgn_sigma : float
        Adds user-defined additive white Gaussian noise to pseduoranges using 1-σ value in meters.
    doppler_awgn_sigma : float
        Adds user-defined additive white Gaussian noise to Doppler using 1-σ value in Hz.
    carrier_phase_awgn_sigma : float
        Adds user-defined additive white Gaussian noise to carrier phase using 1-σ value in cycles.

    Examples
    --------
    >>> gps_constellation = Constellation('GPS', ['L1C'], 10.0)
    >>> measurement_config = MeasurementConfiguration(
    ...     constellation=[gps_constellation],
    ...     rx_clock_type='ocxo',
    ...     rx_noise=True,
    ...     ionosphere=True,
    ...     troposphere=True
    ... )
    """

    constellation: list[Constellation]
    rx_clock_type: str
    rx_noise: bool
    ionosphere: bool
    troposphere: bool
    pseudorange_awgn_sigma: float = 0.0  # [m]
    doppler_awgn_sigma: float = 0.0  # [Hz]
    carrier_phase_awgn_sigma: float = 0.0  # [cycles]


@dataclass
class GeneralConfiguration:
    """
    General simulation parameters and settings.

    This dataclass contains the fundamental parameters that define the
    simulation scenario, including timing, duration, and trajectory information.

    Attributes
    ----------
    initial_datetime : datetime.datetime
        Simulation start datetime. Should be timezone-aware and preferably in UTC.
        This defines the reference time for all simulation calculations.
    duration : float
        Total duration of the simulation in seconds. Determines how long
        the simulation will run from the initial datetime.
    fsim : float
        Simulation step frequency in Hz. This defines the temporal resolution
        of the simulation (e.g., 1.0 Hz = 1 second steps).
    trajectory_name : str
        Name identifier of the trajectory to simulate. This should correspond
        to a trajectory definition available in the navsim `trajectories` folder.

    Examples
    --------
    >>> import datetime as dt
    >>> general_config = GeneralConfiguration(
    ...     initial_datetime=dt.datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc),
    ...     duration=3600.0,
    ...     fsim=1.0,
    ...     trajectory_name='daytona_500_sdx_1s_loop'
    ... )
    """

    initial_datetime: dt.datetime
    duration: float
    fsim: float
    trajectory_name: str


@dataclass
class NavsimConfiguration:
    """
    Complete navigation simulation configuration.

    This is the top-level configuration dataclass that combines all simulation
    parameters into a single coherent configuration object.

    Attributes
    ----------
    general : GeneralConfiguration
        General simulation settings including timing and trajectory information.
    measurement : MeasurementConfiguration
        Measurement-specific simulation settings including constellation
        configurations and error modeling parameters.

    Examples
    --------
    >>> # Assuming general_config and measurement_config are already defined
    >>> full_config = NavsimConfiguration(
    ...     general=general_config,
    ...     measurement=measurement_config
    ... )
    """

    general: GeneralConfiguration
    measurement: MeasurementConfiguration


def load_configuration(dir: str | pl.Path) -> tuple[pl.Path, NavsimConfiguration]:
    """
    Load and preprocess a simulation configuration from a TOML file.

    This function provides an interactive file selection interface to choose
    a configuration file, then parses and validates the TOML content into
    a structured configuration object with proper type checking and preprocessing.

    Parameters
    ----------
    dir : str or pathlib.Path
        Path to the directory containing configuration files. The user will
        be presented with a file selection dialog showing files in this directory.

    Returns
    -------
    tuple of (pathlib.Path, NavsimConfiguration)
        A tuple containing:
        - The path to the selected configuration file
        - The fully parsed and preprocessed simulation configuration object

    Raises
    ------
    FileNotFoundError
        If the user does not select a configuration file or if the selected
        file does not exist.
    tomli.TOMLDecodeError or tomllib.TOMLDecodeError
        If the configuration file cannot be parsed as valid TOML format.
    ValueError
        If any required fields are missing in the configuration file or if
        the configuration structure is invalid.

    Notes
    -----
    The function automatically handles timezone conversion, ensuring that
    datetime objects are converted to UTC if they are not already in UTC.

    Examples
    --------
    >>> import pathlib as pl
    >>> config_dir = pl.Path("./config")
    >>> config_path, config = load_configuration(config_dir)
    >>> print(f"Loaded configuration from: {config_path}")
    >>> print(f"Simulation duration: {config.general.duration} seconds")
    """
    selected_path = select_file(directory=dir, title="navsim")

    with open(selected_path, "rb") as config_file:
        config = tl.load(config_file)

        preprocessed_config = _preprocess_config(config=config)
        loaded_config = _dict_to_dataclass(
            cls=NavsimConfiguration, data=preprocessed_config
        )

        return selected_path, loaded_config


T = TypeVar("T")


def _dict_to_dataclass(cls: Type[T], data: Dict[str, Any]) -> T:
    """
    Convert a dictionary to a dataclass instance with validation.

    This function creates a dataclass instance from a dictionary while
    performing validation to ensure all required fields are present
    and filtering out any extraneous fields not defined in the dataclass.

    Parameters
    ----------
    cls : Type[T]
        The dataclass type to create an instance of.
    data : dict of str to Any
        Dictionary containing the data to populate the dataclass fields.

    Returns
    -------
    T
        An instance of the specified dataclass type populated with the
        provided data.

    Raises
    ------
    ValueError
        If any required fields (those without default values) are missing
        from the input data dictionary.

    Notes
    -----
    This function automatically filters the input data to only include
    fields that are actually defined in the target dataclass, preventing
    errors from extraneous fields in the input data.

    Examples
    --------
    >>> from dataclasses import dataclass
    >>> @dataclass
    ... class Person:
    ...     name: str
    ...     age: int
    ...     city: str = "Unknown"
    >>> data = {"name": "Alice", "age": 30, "extra_field": "ignored"}
    >>> person = _dict_to_dataclass(Person, data)
    >>> print(person.name, person.age, person.city)
    Alice 30 Unknown
    """
    class_fields = {f.name: f for f in fields(cls)}

    required_fields = {
        name
        for name, field in class_fields.items()
        if field.default is field.default_factory is MISSING
    }

    missing_fields = required_fields - set(data.keys())
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    filtered_data = {k: v for k, v in data.items() if k in class_fields}

    return cls(**filtered_data)


def _preprocess_config(config: dict) -> dict:
    """
    Preprocess configuration data before creating dataclass instances.

    This function handles special preprocessing steps required for certain
    configuration fields, such as timezone conversion for datetime objects
    and nested dataclass creation for complex configuration structures.

    Parameters
    ----------
    config : dict
        Raw configuration dictionary loaded from the TOML file.

    Returns
    -------
    dict
        Preprocessed configuration dictionary with properly structured
        dataclass instances and corrected field values.

    Notes
    -----
    This function performs the following preprocessing steps:
    - Converts datetime objects to UTC timezone if they are not already
    - Creates nested Constellation dataclass instances from constellation data
    - Organizes the configuration into the expected hierarchical structure

    The function assumes that the input config dictionary contains both
    general and measurement configuration data at the top level.

    Examples
    --------
    >>> config_dict = {
    ...     'initial_datetime': datetime(2024, 1, 1, 12, 0, 0),
    ...     'duration': 3600.0,
    ...     'fsim': 1.0,
    ...     'trajectory_name': 'test',
    ...     'constellation': [{'reference_constellation': 'GPS', 'signals': ['L1C'], 'mask_angle': 10.0}],
    ...     'rx_clock_type': 'ideal',
    ...     'rx_noise': 'thermal',
    ...     'ionosphere': True,
    ...     'troposphere': True
    ... }
    >>> processed = _preprocess_config(config_dict)
    >>> isinstance(processed['general'], GeneralConfiguration)
    True
    """
    new_config = {}

    general = _dict_to_dataclass(cls=GeneralConfiguration, data=config)

    if not general.initial_datetime.tzinfo == dt.timezone.utc:
        general.initial_datetime = general.initial_datetime.astimezone(ZoneInfo("UTC"))

    new_config["general"] = general

    measurement = _dict_to_dataclass(cls=MeasurementConfiguration, data=config)
    measurement.constellation = [
        _dict_to_dataclass(cls=Constellation, data=constellation)
        for constellation in measurement.constellation
    ]
    new_config["measurement"] = measurement

    return new_config
