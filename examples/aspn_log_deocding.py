import lcm
import numpy as np
from navtools.aspn import AspnDecoderLcm

LOG_PATH = "/home/tkoza/Devel/utils/navsuite/src/navsim/logs/2024-06-14_00:00:00Z_example_galileo-iridium.log"

SATNAV_CHANNEL = "aspn23://navsim/measurement_satnav_with_sv_data"
TRUE_POSITION_CHANNEL = "aspn23://navsim/true_measurement_position"
TRUE_VELOCITY_CHANNEL = "aspn23://navsim/true_measurement_velocity"

log = lcm.EventLog(path=LOG_PATH)
decoder = AspnDecoderLcm()

for event in log:
    if event.channel == SATNAV_CHANNEL:
        standard, data = decoder.decode(msg=event)

        # processing example
        sv_ids = [
            (obs.satellite_system, obs.prn, obs.signal_descriptor) for obs in data.obs
        ]
        pranges = [obs.pseudorange for obs in data.obs]
        dopplers = [obs.pseudorange_rate for obs in data.obs]

        msg = f"""Observables:
                    SV ID [System, PRN, Signal]: {sv_ids}
                    Pseudoranges [m]: {pranges}
                    Dopplers [Hz]: {dopplers}"""
        print(msg)

    if event.channel == TRUE_POSITION_CHANNEL:
        standard, data = decoder.decode(msg=event)

        lla = (float(np.degrees(data.term1)), float(np.degrees(data.term2)), data.term3)
        msg = f"True Position LLA [deg, deg, m]: {lla}"
        print(msg)

    if event.channel == TRUE_VELOCITY_CHANNEL:
        standard, data = decoder.decode(msg=event)

        ecef_vel = (data.x, data.y, data.z)
        msg = f"True Velocity ECEF [m/s]: {ecef_vel}"
        print(msg)
