import datetime as dt
import pathlib as pl
from collections import defaultdict

import numpy as np

from navtools.conversions import datetime_to_gps


def parse_tle(file_path: str | pl.Path, min_inclination: float | None = None):
    tle_entries = {}

    with open(file_path, "r") as file:
        lines = file.readlines()

        for sv_idx in range(0, len(lines), 3):
            line1 = lines[sv_idx + 1]
            line2 = lines[sv_idx + 2]

            # filter entries by inclination
            if min_inclination is not None:
                line2_fields = line2.split()
                inclination = float(line2_fields[2])

                if inclination < np.abs(min_inclination):
                    continue

            tle_entries[lines[sv_idx].strip()] = [
                line1,
                line2,
            ]

    return tle_entries


def parse_sp3(file_path: str | pl.Path, valid_constellations: str | list[str]):
    if isinstance(valid_constellations, str):
        valid_constellations = [valid_constellations]

    entry_time = defaultdict(list)
    entry_states = defaultdict(list)
    sp3_entries = {}

    with open(file_path, "r") as f:
        lines = f.readlines()

        current_time = None
        for line in lines:
            if line.startswith("*"):
                parts = line.split()
                current_time = dt.datetime(
                    int(parts[1]),
                    int(parts[2]),
                    int(parts[3]),
                    int(parts[4]),
                    int(parts[5]),
                    int(float(parts[6])),
                    tzinfo=dt.timezone.utc,
                )
                gps_seconds, _, _ = datetime_to_gps(datetime=current_time)

            elif line.startswith("P") and current_time:
                prn = line[1:4]

                if prn[0] in valid_constellations:
                    x = float(line[4:18]) * 1e3
                    y = float(line[18:32]) * 1e3
                    z = float(line[32:46]) * 1e3
                    clk = float(line[46:60]) * 1e-6

                    entry_time[prn].append(gps_seconds)
                    entry_states[prn].append([x, y, z, clk])

    for prn in entry_time.keys():
        time = np.array(entry_time[prn]).squeeze()
        states = np.array(entry_states[prn]).squeeze()

        sp3_entries[prn] = [time, states]

    return sp3_entries
