import numpy as np

import datetime as dt


from navsim.io import CONFIG_PATH
from navsim.simulations import (
    load_configuration,
    MeasurementSimulation,
)
from navsim.trajectories import (
    load_sample_trajectory,
    translate_trajectory,
    interpolate_trajectory,
)


def main():
    config = load_configuration(dir=CONFIG_PATH, sim_type="measurement")

    # extract configuration lists
    constellations = [c.reference_constellation for c in config.constellations]
    mask_angles = [c.mask_angle for c in config.constellations]

    # create elapsed timeseries and timestamps
    sim_timeseries, sim_timestamps = generate_timeseries(
        initial_time=config.initial_datetime,  # config.initial_datetime is UTC referenced
        duration=config.duration,
        fsim=config.fsim,
    )

    # load and modify trajectory
    traj_timeseries, traj_lat, traj_lon, traj_alt = load_sample_trajectory(
        trajectory_name=config.trajectory_name
    )
    rx_pos, rx_vel = interpolate_trajectory(
        time=traj_timeseries,
        lat=traj_lat,
        lon=traj_lon,
        alt=traj_alt,
        new_time=sim_timeseries,
        deg=True,
    )
    rx_pos = np.array(rx_pos).transpose()
    rx_vel = np.array(rx_vel).transpose()

    # create simulation and begin
    sim = MeasurementSimulation(constellations=constellations, mask_angles=mask_angles)
    sim.simulate(utc_timestamps=sim_timestamps, rx_pos=rx_pos, rx_vel=rx_vel)

    pass


def generate_timeseries(initial_time: dt.datetime, duration: float, fsim: float):
    tsim = 1 / fsim
    nperiods = int(np.ceil(duration / tsim)) + 1

    timeseries = np.linspace(start=0, stop=duration, num=nperiods)
    timestamps = [initial_time + dt.timedelta(seconds=step) for step in timeseries]

    return timeseries, timestamps


if __name__ == "__main__":
    main()
