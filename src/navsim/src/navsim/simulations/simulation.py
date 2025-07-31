__all__ = ["simulate", "main"]

import argparse
import datetime as dt
import pathlib as pl
from typing import Optional

import numpy as np
from numpy.typing import ArrayLike, NDArray

from navsim.io import CONFIG_PATH, LOG_PATH
from navsim.simulations import MeasurementSimulation, load_configuration
from navsim.trajectories import interpolate_trajectory, load_sample_trajectory


def simulate(config_dir: Optional[pl.Path] = None, log_dir: Optional[pl.Path] = None):
    """
    Run a full satellite navigation simulation and write results to an LCM log.

    Loads configuration files, generates timelines, interpolates trajectories,
    and runs the measurement simulation. Results are output in an LCM log file
    in a timestamped subdirectory.

    Parameters
    ----------
    config_dir : pathlib.Path or None
        Directory containing configuration files. If None, uses the default
        path `navsim.io.CONFIG_PATH`.
    log_dir : pathlib.Path or None
        Directory to write output log files. If None, defaults to `LOG_PATH`
        defined in `navsim.io`.

    Raises
    ------
    FileNotFoundError
        If required configuration files are missing in `config_dir`.
    PermissionError
        If log directory cannot be created or written to.

    Examples
    --------
    >>> simulate(config_dir=Path("cfg"), log_dir=Path("logs"))
    """
    # use provided config directory and log directory or fall back to default
    if config_dir is None:
        config_dir = CONFIG_PATH
    else:
        config_dir = pl.Path(config_dir)

    if log_dir is None:
        log_dir = LOG_PATH
    else:
        log_dir = pl.Path(log_dir)

    log_dir.mkdir(parents=True, exist_ok=True)

    # load configuration and create output LCM log path
    config_path, config = load_configuration(dir=config_dir)
    lcm_log_path = create_lcm_log_path(
        initial_datetime=config.general.initial_datetime,
        config_path=config_path,
        log_dir=log_dir,
    )

    # create elapsed timeseries and timestamps
    sim_timeseries, sim_datetimes = generate_timeseries(
        initial_datetime=config.general.initial_datetime,
        duration=config.general.duration,
        fsim=config.general.fsim,
    )

    # create trajectory from navsim defaults
    rx_pos, rx_vel = create_trajectory(
        trajectory_name=config.general.trajectory_name,
        sim_timeseries=sim_timeseries,
        is_static=config.general.is_static,
    )

    # create simulation and begin
    sim = MeasurementSimulation(config=config.measurement)
    sim.simulate_to_lcm(
        utc_timestamps=sim_datetimes,
        rx_pos=rx_pos,
        rx_vel=rx_vel,
        log_path=lcm_log_path,
    )


def create_lcm_log_path(
    initial_datetime: dt.datetime, config_path: pl.Path, log_dir: pl.Path
) -> pl.Path:
    """
    Create a timestamped LCM log filename based on the initial datetime.

    Parameters
    ----------
    initial_datetime : datetime.datetime
        UTC start time of the simulation.
    config_path : pathlib.Path
        Path to the configuration file used for the simulation.

    Returns
    -------
    pathlib.Path
        Full path to the output LCM log under `LOG_PATH`.

    Examples
    --------
    >>> from datetime import datetime
    >>> from pathlib import Path
    >>> dt0 = datetime(2025, 7, 21, 12, 0)
    >>> p = Path("config.yaml")
    >>> str(create_lcm_log_path(dt0, p)).endswith("_config.log")
    True
    """
    log_name = (
        f"{initial_datetime.strftime('%Y-%m-%d_%H:%M:%SZ')}_{config_path.stem}.log"
    )
    lcm_log_path = log_dir / log_name
    return lcm_log_path


def generate_timeseries(
    initial_datetime: dt.datetime,
    duration: float,
    fsim: float,
) -> tuple[list[float], list[dt.datetime]]:
    """
    Generate elapsed time points and corresponding UTC datetime stamps.

    Parameters
    ----------
    initial_datetime : datetime.datetime
        UTC start time for the simulation time series.
    duration : float
        Total simulation duration in seconds.
    fsim : float
        Simulation sampling frequency in Hz.

    Returns
    -------
    timeseries : list of float
        Elapsed time values from t=0 to t=duration.
    datetimes : list of datetime.datetime
        UTC timestamps corresponding to each elapsed time.

    Examples
    --------
    >>> from datetime import datetime
    >>> t, ts = generate_timeseries(datetime(2025,1,1), 10.0, 1.0)
    >>> len(t), ts[0], ts[-1]
    (11, datetime.datetime(2025, 1, 1, 0, 0), datetime.datetime(2025, 1, 1, 0, 0, 10))
    """
    tsim = 1.0 / fsim
    nperiods = int(np.ceil(duration / tsim)) + 1
    timeseries = np.linspace(start=0.0, stop=duration, num=nperiods).tolist()
    datetimes = [initial_datetime + dt.timedelta(seconds=step) for step in timeseries]

    return timeseries, datetimes


def create_trajectory(
    trajectory_name: str, sim_timeseries: ArrayLike, is_static: bool
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Load and interpolate a predefined trajectory to simulation times.

    Parameters
    ----------
    trajectory_name : str
        Name of the sample trajectory to load.
    sim_timeseries : array-like of float
        Elapsed simulation times at which to interpolate.
    is_static : bool
        Determines whether the entire duration is static at the first point in the selected trajectory.

    Returns
    -------
    rx_pos : numpy.ndarray of float64, shape (N, 3)
        Receiver ECEF positions (meters) at each simulation time.
    rx_vel : numpy.ndarray of float64, shape (N, 3)
        Receiver ECEF velocities (m/s) at each simulation time.

    Notes
    -----
    If the simulation duration exceeds the trajectory duration,
    the last valid ECEF position and velocity are repeated.
    """
    traj_timeseries, traj_lat, traj_lon, traj_alt = load_sample_trajectory(
        trajectory_name=trajectory_name
    )

    if is_static:
        traj_lat = np.repeat(traj_lat[0], traj_timeseries.size)
        traj_lon = np.repeat(traj_lon[0], traj_timeseries.size)
        traj_alt = np.repeat(traj_alt[0], traj_timeseries.size)

    rx_pos_ecef, rx_vel_ecef = interpolate_trajectory(
        time=traj_timeseries,
        lat=traj_lat,
        lon=traj_lon,
        alt=traj_alt,
        new_time=sim_timeseries,
        deg=True,
        include_accel=False,
    )
    rx_pos = np.array(rx_pos_ecef).transpose()
    rx_vel = np.array(rx_vel_ecef).transpose()

    nan_mask = np.any(np.isnan(rx_pos), axis=1)
    valid_idx = np.flatnonzero(~nan_mask)

    # repeat last valid state
    if valid_idx.size:
        last = valid_idx.max()
        rx_pos[nan_mask] = rx_pos[last]
        rx_vel[nan_mask] = rx_vel[last]

    return rx_pos, rx_vel


def main():
    """
    Command-line entry point for the navsim simulation.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="Run a satellite navigation simulation",
    )
    parser.add_argument(
        "--config-dir",
        type=pl.Path,
        help="Directory containing configuration files (default: uses package default)",
    )
    parser.add_argument(
        "--log-dir",
        type=pl.Path,
        help=(
            "Directory to write log files to (default):\n"
            "  • Linux/macOS: ~/.navsim/logs/\n"
            "  • Windows:     C:\\Users\\<user>\\.navsim\\logs/"
        ),
    )
    args = parser.parse_args()
    simulate(config_dir=args.config_dir, log_dir=args.log_dir)


if __name__ == "__main__":
    main()
