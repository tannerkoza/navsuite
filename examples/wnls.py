import lcm
import matplotlib.pyplot as plt
import numpy as np
from navgnss.navigators import WNLS, WNLSConfiguration
from navgnss.observables import ObservablePreprocessor, aspn2observables
from navplot.geo import GeoplotData, igeoplot
from navtools.aspn import AspnDecoderLcm
from navtools.conversions.coordinates import (
    ecef2enu,
    ecef2enuv,
    ecef2geodetic,
    geodetic2ecef,
)

LOG_PATH = "/home/tkoza/.navsim/logs/2025-06-14_00:00:00Z_example_gps-beidou.log"

SATNAV_CHANNEL = "aspn23://navsim/measurement_satnav_with_sv_data"
TRUE_POSITION_CHANNEL = "aspn23://navsim/true_measurement_position"
TRUE_VELOCITY_CHANNEL = "aspn23://navsim/true_measurement_velocity"

# pre-processing configuration
INCLUDED_SYSTEMS = ["globalstar"]
INCLUDED_SIGNALS = []

# WNLS configuration
WNLS_CONFIG = WNLSConfiguration(
    reference_system="gps", is_weighted=True, include_velocity=True
)


def main():
    wnls = WNLS(configuration=WNLS_CONFIG)

    log = lcm.EventLog(path=LOG_PATH)
    decoder = AspnDecoderLcm()

    ecef_wnls_log = []
    ecef_vel_wnls_log = []
    ecef_ref_log = []
    ecef_vel_ref_log = []
    lla_ref_log = []

    for event in log:
        _, data = decoder.decode(msg=event)

        if event.channel == SATNAV_CHANNEL:
            raw_observables = aspn2observables(satnav_msg=data)
            observable_preprocessor = ObservablePreprocessor(
                raw_observables=raw_observables
            )

            if INLCUDED_SYSTEMS:
                observable_preprocessor.filter_by_system(systems=INLCUDED_SYSTEMS)

            if INCLUDED_SIGNALS:
                observable_preprocessor.filter_by_signal(signals=INCLUDED_SIGNALS)

            observables = observable_preprocessor.filtered_observables

            wnls.update(observables=observables)
            ecef_rx_pos = wnls.position
            ecef_wnls_log.append(ecef_rx_pos)
            ecef_rx_vel = wnls.velocity
            ecef_vel_wnls_log.append(ecef_rx_vel)

        if event.channel == TRUE_POSITION_CHANNEL:
            lla_ref = [np.degrees(data.term1), np.degrees(data.term2), data.term3]
            lla_ref_log.append(lla_ref)

            ecef_ref = np.array(
                geodetic2ecef(lat=lla_ref[0], lon=lla_ref[1], alt=lla_ref[2], deg=True)
            )
            ecef_ref_log.append(ecef_ref)

        if event.channel == TRUE_VELOCITY_CHANNEL:
            ecef_vel = (data.x, data.y, data.z)
            ecef_vel_ref_log.append(ecef_vel)

    plot(ecef_wnls_log, ecef_vel_wnls_log, ecef_ref_log, ecef_vel_ref_log, lla_ref_log)


def plot(ecef_wnls_log, ecef_vel_wnls_log, ecef_ref_log, ecef_vel_ref_log, lla_ref_log):
    ecef_wnls_log = np.array(ecef_wnls_log)
    ecef_vel_wnls_log = np.array(ecef_vel_wnls_log)
    ecef_ref_log = np.array(ecef_ref_log)
    ecef_vel_ref_log = np.array(ecef_vel_ref_log)

    lat_wnls, lon_wnls, alt_wnls = np.array(
        ecef2geodetic(
            x=ecef_wnls_log[:, 0], y=ecef_wnls_log[:, 1], z=ecef_wnls_log[:, 2]
        )
    )
    lla_wnls_log = np.array([np.degrees(lat_wnls), np.degrees(lon_wnls), alt_wnls])
    lla_ref_log = np.array(lla_ref_log).transpose()

    enu_wnls_log = np.array(
        ecef2enu(
            x=ecef_wnls_log[:, 0],
            y=ecef_wnls_log[:, 1],
            z=ecef_wnls_log[:, 2],
            lat0=lla_ref_log[0, 0],
            lon0=lla_ref_log[1, 0],
            alt0=lla_ref_log[2, 0],
            deg=True,
        )
    ).transpose()
    enu_vel_wnls_log = np.array(
        ecef2enuv(
            x=ecef_vel_wnls_log[:, 0],
            y=ecef_vel_wnls_log[:, 1],
            z=ecef_vel_wnls_log[:, 2],
            lat0=lla_ref_log[0, 0],
            lon0=lla_ref_log[1, 0],
            deg=True,
        )
    ).transpose()
    enu_ref_log = np.array(
        ecef2enu(
            x=ecef_ref_log[:, 0],
            y=ecef_ref_log[:, 1],
            z=ecef_ref_log[:, 2],
            lat0=lla_ref_log[0, 0],
            lon0=lla_ref_log[1, 0],
            alt0=lla_ref_log[2, 0],
            deg=True,
        )
    ).transpose()
    enu_vel_ref_log = np.array(
        ecef2enuv(
            x=ecef_vel_ref_log[:, 0],
            y=ecef_vel_ref_log[:, 1],
            z=ecef_vel_ref_log[:, 2],
            lat0=lla_ref_log[0, 0],
            lon0=lla_ref_log[1, 0],
            deg=True,
        )
    ).transpose()

    wnls_sol = GeoplotData(
        label="WNLS", lat=lla_wnls_log[0], lon=lla_wnls_log[1], alt=lla_wnls_log[2]
    )
    ref_sol = GeoplotData(
        label="Truth", lat=lla_ref_log[0], lon=lla_ref_log[1], alt=lla_ref_log[2]
    )

    igeoplot([wnls_sol, ref_sol], size=20, color_palette="Spectral")

    fig, ax = plt.subplots(nrows=3, sharex=True)

    ax[0].plot(enu_wnls_log[:, 0], label="WNLS")
    ax[1].plot(enu_wnls_log[:, 1], label="WNLS")
    ax[2].plot(enu_wnls_log[:, 2], label="WNLS")
    ax[0].plot(enu_ref_log[:, 0], label="Truth")
    ax[1].plot(enu_ref_log[:, 1], label="Truth")
    ax[2].plot(enu_ref_log[:, 2], label="Truth")

    fig.suptitle("ENU Position Comparison")
    ax[0].set_xlabel("East [m]")
    ax[1].set_xlabel("North [m]")
    ax[2].set_xlabel("Up [m]")
    fig.supxlabel("Samples")

    handles, labels = ax[0].get_legend_handles_labels()
    fig.legend(handles, labels)

    plt.tight_layout()

    fig, ax = plt.subplots(nrows=3, sharex=True)

    ax[0].plot(enu_wnls_log[:, 0] - enu_ref_log[:, 0])
    ax[1].plot(enu_wnls_log[:, 1] - enu_ref_log[:, 1])
    ax[2].plot(enu_wnls_log[:, 2] - enu_ref_log[:, 2])

    fig.suptitle("ENU Position Error")
    ax[0].set_xlabel("East [m]")
    ax[1].set_xlabel("North [m]")
    ax[2].set_xlabel("Up [m]")
    fig.supxlabel("Samples")

    plt.tight_layout()

    fig, ax = plt.subplots(nrows=3, sharex=True)

    ax[0].plot(enu_vel_wnls_log[:, 0], label="WNLS")
    ax[1].plot(enu_vel_wnls_log[:, 1], label="WNLS")
    ax[2].plot(enu_vel_wnls_log[:, 2], label="WNLS")
    ax[0].plot(enu_vel_ref_log[:, 0], label="Truth")
    ax[1].plot(enu_vel_ref_log[:, 1], label="Truth")
    ax[2].plot(enu_vel_ref_log[:, 2], label="Truth")

    fig.suptitle("ENU Velocity Comparison")
    ax[0].set_xlabel("East [m/s]")
    ax[1].set_xlabel("North [m/s]")
    ax[2].set_xlabel("Up [m/s]")
    fig.supxlabel("Samples")

    handles, labels = ax[0].get_legend_handles_labels()
    fig.legend(handles, labels)

    plt.tight_layout()

    fig, ax = plt.subplots(nrows=3, sharex=True)

    ax[0].plot(enu_vel_wnls_log[:, 0] - enu_vel_ref_log[:, 0])
    ax[1].plot(enu_vel_wnls_log[:, 1] - enu_vel_ref_log[:, 1])
    ax[2].plot(enu_vel_wnls_log[:, 2] - enu_vel_ref_log[:, 2])

    fig.suptitle("ENU Velocity Error")
    ax[0].set_xlabel("East [m/s]")
    ax[1].set_xlabel("North [m/s]")
    ax[2].set_xlabel("Up [m/s]")
    fig.supxlabel("Samples")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
