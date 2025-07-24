import numpy as np
import pathlib as pl

import requests

from navtools.io import FileDownloader


import re
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import pandas as pd

import matplotlib.pyplot as plt


@dataclass
class ITCEphemerisEntry:
    """Represents a single ITC ephemeris entry"""

    timestamp: datetime
    position: np.ndarray  # [x, y, z] in km
    velocity: np.ndarray  # [vx, vy, vz] in km/s
    covariance_lower_tri: np.ndarray  # 21 elements of 6x6 lower triangular matrix


class ITCEphemerisParser:
    """Parser for modified ITC ephemeris files per 18th Space Control Squadron format"""

    def __init__(self):
        self.header_lines = []
        self.reference_frame = None
        self.entries = []

    def parse_file(self, filepath: str) -> List[ITCEphemerisEntry]:
        """Parse an ITC ephemeris file and return list of entries"""
        with open(filepath, "r") as f:
            content = f.read()

        return self.parse_content(content)

    def parse_content(self, content: str) -> List[ITCEphemerisEntry]:
        """Parse ephemeris content from string"""
        lines = [line.strip() for line in content.strip().split("\n") if line.strip()]

        # Parse header (first 3 lines)
        self.header_lines = lines[:3]

        # Parse reference frame (4th line, must be UVW)
        if len(lines) < 4:
            raise ValueError(
                "File must have at least 4 lines (3 header + reference frame)"
            )

        self.reference_frame = lines[3]
        if self.reference_frame != "UVW":
            raise ValueError(
                f"Reference frame must be 'UVW', got '{self.reference_frame}'"
            )

        # Parse data blocks (starting from line 5)
        data_lines = lines[4:]
        self.entries = self._parse_data_blocks(data_lines)

        return self.entries

    def _parse_data_blocks(self, lines: List[str]) -> List[ITCEphemerisEntry]:
        """Parse data blocks, each consisting of 4 lines"""
        entries = []

        if len(lines) % 4 != 0:
            raise ValueError(
                f"Data section must have multiple of 4 lines, got {len(lines)} lines"
            )

        # Process blocks of 4 lines
        for i in range(0, len(lines), 4):
            block = lines[i : i + 4]

            try:
                entry = self._parse_single_block(block)
                entries.append(entry)
            except Exception as e:
                print(f"Warning: Could not parse block starting at line {i+5}: {e}")
                continue

        return entries

    def _parse_single_block(self, block: List[str]) -> ITCEphemerisEntry:
        """Parse a single 4-line block"""
        if len(block) != 4:
            raise ValueError(f"Block must have exactly 4 lines, got {len(block)}")

        # Parse first line: timestamp + position + velocity
        line1_parts = block[0].split()
        if len(line1_parts) != 7:
            raise ValueError(f"First line must have 7 values, got {len(line1_parts)}")

        # Parse timestamp
        timestamp = self._parse_timestamp(line1_parts[0])

        # Parse position (km)
        position = np.array(
            [float(line1_parts[1]), float(line1_parts[2]), float(line1_parts[3])]
        )

        # Parse velocity (km/s)
        velocity = np.array(
            [float(line1_parts[4]), float(line1_parts[5]), float(line1_parts[6])]
        )

        # Parse covariance matrix from next 3 lines (21 values total)
        covariance_values = []
        for line in block[1:4]:
            parts = line.split()
            if len(parts) != 7:
                raise ValueError(
                    f"Covariance line must have 7 values, got {len(parts)}"
                )
            covariance_values.extend([float(val) for val in parts])

        if len(covariance_values) != 21:
            raise ValueError(
                f"Expected 21 covariance values, got {len(covariance_values)}"
            )

        covariance_lower_tri = np.array(covariance_values)

        return ITCEphemerisEntry(
            timestamp=timestamp,
            position=position,
            velocity=velocity,
            covariance_lower_tri=covariance_lower_tri,
        )

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp from yyyyDOYhhmmss.sss format"""
        # Match format: yyyyDOYhhmmss.sss
        match = re.match(r"(\d{4})(\d{3})(\d{2})(\d{2})(\d{2})\.(\d{3})", timestamp_str)

        if not match:
            raise ValueError(
                f"Invalid timestamp format: {timestamp_str}. Expected yyyyDOYhhmmss.sss"
            )

        year = int(match.group(1))
        day_of_year = int(match.group(2))
        hour = int(match.group(3))
        minute = int(match.group(4))
        second = int(match.group(5))
        millisecond = int(match.group(6))

        # Create datetime from year and day of year
        base_date = datetime(year, 1, 1)
        target_date = base_date + timedelta(days=day_of_year - 1)

        return target_date.replace(
            hour=hour, minute=minute, second=second, microsecond=millisecond * 1000
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Convert parsed entries to pandas DataFrame"""
        if not self.entries:
            return pd.DataFrame()

        data = []
        for entry in self.entries:
            row = {
                "timestamp": entry.timestamp,
                "x": entry.position[0],
                "y": entry.position[1],
                "z": entry.position[2],
                "vx": entry.velocity[0],
                "vy": entry.velocity[1],
                "vz": entry.velocity[2],
            }

            # Add covariance matrix elements
            for i, val in enumerate(entry.covariance_lower_tri):
                row[f"cov_{i+1}"] = val

            data.append(row)

        return pd.DataFrame(data)

    def get_covariance_matrix(self, entry_index: int) -> np.ndarray:
        """Get full 6x6 covariance matrix for a specific entry"""
        if entry_index >= len(self.entries):
            raise IndexError(f"Entry index {entry_index} out of range")

        entry = self.entries[entry_index]
        lower_tri = entry.covariance_lower_tri

        # Create 6x6 symmetric matrix from lower triangular elements
        matrix = np.zeros((6, 6))

        # Fill lower triangular part
        idx = 0
        for i in range(6):
            for j in range(i + 1):
                matrix[i, j] = lower_tri[idx]
                matrix[j, i] = lower_tri[idx]  # Symmetric
                idx += 1

        return matrix

    def get_header_info(self) -> dict:
        """Get parsed header information"""
        return {
            "header_lines": self.header_lines,
            "reference_frame": self.reference_frame,
            "num_entries": len(self.entries),
        }


import asyncio
import aiohttp
import numpy as np
from concurrent.futures import ThreadPoolExecutor


async def fetch_files_async(files, api_url, max_concurrent=20):
    """Fetch files asynchronously"""
    files_data = {}

    connector = aiohttp.TCPConnector(limit=max_concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_file(file):
            async with semaphore:
                try:
                    async with session.get(api_url + file) as response:
                        content = await response.text()
                        return file, content
                except Exception as e:
                    print(f"Error fetching {file}: {e}")
                    return file, None

        # Create tasks for all files
        tasks = [fetch_file(file) for file in files]

        # Execute all tasks
        results = await asyncio.gather(*tasks)

        # Store results
        for file, content in results:
            if content is not None:
                files_data[file] = content

    return files_data


# Usage:
# pos_cov_per_file = await process_files_concurrent(lines, api_url, parser)


import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize, curve_fit
from scipy.stats import norm
import pandas as pd




# Example usage
def main():
    """Example usage of the ITC ephemeris parser"""

    api_url = "https://api.starlink.com/public-files/ephemerides/"
    file_manifest_url = api_url + "MANIFEST.txt"

    downloader = FileDownloader()
    file_manifest = downloader.download(url=file_manifest_url)

    with open(file=file_manifest, mode="r") as f:
        files = f.read().splitlines()

    data = fetch_files_async(files=files[:50], api_url=api_url)
    real_data = asyncio.run(data)

    parser = ITCEphemerisParser()

    pos_cov_per_file = []
    pos_per_file = []

    for name, raw_eph in real_data.items():
        sv_name = name.split("_")[2]
        entries = parser.parse_content(raw_eph)

        dt = np.array([e.timestamp for e in entries])
        cov_std = [
            np.sqrt(np.diag(parser.get_covariance_matrix(idx)))
            for idx in range(len(entries))
        ]
        cov_std_arr = np.array(cov_std) * 1000  # [m]

        pos = [e.position * 1000 for e in entries]

        pos_cov_per_file.append(cov_std_arr)
        pos_per_file.append(pos)

    mean = np.mean(np.array(pos_cov_per_file), axis=0)
    # new_mean = np.where(mean > 10, np.nan, mean)
    dt_fit = dt
    ts_fit = np.array([d.timestamp() for d in dt_fit])
    ts_pred = np.array([d.timestamp() for d in dt])
    print((ts_pred.max() - ts_pred.min()) / 3600)

    # pos_mag = np.linalg.norm(mean[:1000, :3], axis=1)

    # gm = GaussMarkovProcess()
    # gm.fit_ar1(ts_fit, pos_mag)
    # # gm.plot_fit(ts, pos_mag)

    # # Fit polynomial of degree 3
    # coeffs = np.polyfit(ts_fit, pos_mag, deg=3)
    # poly_func = np.poly1d(coeffs)

    # # Generate fitted curve
    # x_fit = np.linspace(ts_pred.min(), ts_pred.max(), ts_pred.size)
    # y_fit = poly_func(x_fit)

    # sigma = np.std(pos_mag - y_fit)
    # noise = sigma * np.random.randn(y_fit.size)

    # from scipy.interpolate import PchipInterpolator

    # Make predictions

    plt.figure()
    plt.title("Position")
    plt.plot(dt_fit, mean[:, :3])
    plt.figure()
    plt.title("Velocity")
    plt.plot(dt_fit, mean[:, 3:])
    # plt.plot(ts_fit, pos_mag)
    # plt.plot(x_fit, y_fit)
    # plt.plot(x_fit, y_fit2)
    # plt.hlines(y=10, xmin=dt.min(), xmax=dt.max())
    plt.xlabel("Datetime")
    plt.ylabel("Position Covariance RTN (m)")

    plt.show()
    # Create parser instance

    # Parse the sample data

    # Display header info
    # print("Header Information:")
    # header_info = parser.get_header_info()
    # for key, value in header_info.items():
    #     print(f"  {key}: {value}")

    # # Display parsed entries
    # print(f"\nParsed {len(entries)} entries")
    # if entries:
    #     print("\nFirst entry details:")
    #     entry = entries[0]
    #     print(f"  Timestamp: {entry.timestamp}")
    #     print(
    #         f"  Position (km): [{entry.position[0]:.6f}, {entry.position[1]:.6f}, {entry.position[2]:.6f}]"
    #     )
    #     print(
    #         f"  Velocity (km/s): [{entry.velocity[0]:.6f}, {entry.velocity[1]:.6f}, {entry.velocity[2]:.6f}]"
    #     )
    #     print(f"  Covariance elements: {len(entry.covariance_lower_tri)}")

    #     # Show full 6x6 covariance matrix
    #     print(f"\nFull 6x6 covariance matrix:")
    #     cov_matrix = parser.get_covariance_matrix(0)
    #     print(cov_matrix)

    # # Convert to DataFrame
    # df = parser.to_dataframe()
    # print(f"\nDataFrame shape: {df.shape}")
    # if not df.empty:
    #     print("DataFrame columns:", df.columns.tolist())
    #     print(f"\nTime span: {df['timestamp'].min()} to {df['timestamp'].max()}")

    #     # Show position statistics
    #     print(f"\nPosition statistics (km):")
    #     print(f"  X: {df['x'].min():.1f} to {df['x'].max():.1f}")
    #     print(f"  Y: {df['y'].min():.1f} to {df['y'].max():.1f}")
    #     print(f"  Z: {df['z'].min():.1f} to {df['z'].max():.1f}")

    # return parser, entries, df


if __name__ == "__main__":
    main()
