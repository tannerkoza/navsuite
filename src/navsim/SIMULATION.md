# navsim Simulation Guide

This guide explains how to configure navigation simulations using the navsim configuration system. navsim uses TOML files to define simulation parameters, making it easy to create reproducible and shareable simulation scenarios.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration File Structure](#configuration-file-structure)
- [General Settings](#general-settings)
- [Measurement Configuration](#measurement-configuration)
- [Constellation Configuration](#constellation-configuration)
- [Error Modeling](#error-modeling)
- [Complete Example](#complete-example)
- [Loading Configurations](#loading-configurations)
- [Troubleshooting](#troubleshooting)

## Quick Start

1. Create a TOML configuration file in `src/navsim/config` (e.g., `my_simulation.toml`)
2. Define your simulation parameters using the structure described below
3. Run the navsim executable (with optional arguments):

```shell
navsim
```

## Configuration File Structure

navsim configuration files use TOML format and are organized into several sections:

- **General Settings**: Simulation timing, duration, and trajectory
- **Error Modeling**: Receiver characteristics and atmospheric effects
- **Constellation Configuration**: Satellite constellation definitions

## General Settings

The general section defines the fundamental simulation parameters:

### `initial_datetime`

- **Type**: ISO 8601 datetime string
- **Description**: Simulation start time
- **Format**: `YYYY-MM-DDTHH:MM:SS+TZ:TZ` or `YYYY-MM-DDTHH:MM:SS-TZ:TZ`
- **Example**: `2024-06-14T00:00:00-00:00`

### `duration`

- **Type**: Float
- **Units**: Seconds
- **Description**: Total simulation duration
- **Example**: `7200` (2 hours)

### `fsim`

- **Type**: Float
- **Units**: Hz
- **Description**: Simulation step frequency (temporal resolution)
- **Example**: `1` (1 Hz = 1-second steps)
- **Common Values**:
  - `1.0` - Standard resolution
  - `10.0` - High resolution
  - `0.1` - Low resolution for long simulations

### `trajectory_name`

- **Type**: String
- **Description**: Identifier for the trajectory to simulate
- **Example**: `"road_finland_sdx_01_onego"`
- **Notes**: Must correspond to an available trajectory in your simulation system

### `is_static`

- **Type**: Boolean
- **Description**: Optional ability to set receiver at static at starting position of trajectory defined by `trajectory_name`
- **Example**: `true`

## Measurement Configuration

### Error Modeling Parameters

### `rx_clock_type`

- **Type**: String
- **Description**: Receiver clock model type
- **Options**:
  - `"low_quality_tcxo"` - Low-Quality Temperature-Compensated Crystal Oscillator
  - `"high_quality_tcxo"` - High-Quality Temperature-Compensated Crystal Oscillator
  - `"ocxo"` - Oven-Controlled Crystal Oscillator
  - `"rubidium"` - Rubidium Atomic Clock
  - `"cesium"` - Cesium Atomic Clock
- **Example**: `"ocxo"`

### `rx_noise`

- **Type**: Boolean
- **Description**: Enable realistic thermal noise modeling
- **Example**: `true`

### `ionosphere`

- **Type**: Boolean
- **Description**: Enable ionospheric delay modeling
- **Example**: `true`
- **Notes**: Models signal delays caused by charged particles in the ionosphere

### `troposphere`

- **Type**: Boolean
- **Description**: Enable tropospheric delay modeling
- **Example**: `false`
- **Notes**: Models signal delays caused by water vapor and atmospheric pressure

### `pseudorange_awgn_sigma`

- **Type**: Float
- **Description**: Optional 1-σ value (in meters) for generating user-defined additive white Gaussian pseudorange noise
- **Example**: `5.0`
- **Notes**: Can replace or supplement `rx_noise`, which is based on carrier-to-noise density ratio

### `doppler_awgn_sigma`

- **Type**: Float
- **Description**: Optional 1-σ value (in Hz) for generating user-defined additive white Gaussian Doppler noise
- **Example**: `2.0`
- **Notes**: Can replace or supplement `rx_noise`, which is based on carrier-to-noise density ratio

### `carrier_phase_awgn_sigma`

- **Type**: Float
- **Description**: Optional 1-σ value (in cycles) for generating user-defined additive white Gaussian carrier phase noise
- **Example**: `0.2`
- **Notes**: Can replace or supplement `rx_noise`, which is based on carrier-to-noise density ratio

## Constellation Configuration

Constellations are defined as arrays using the `[[constellation]]` TOML array syntax. You can define multiple constellations in a single simulation.

### `reference_constellation`

- **Type**: String
- **Description**: Name of the satellite constellation
- **Options**: [Supported Constellations](./CONSTELLATIONS.md)
- **Example**: `"gps"`

### `signals`

- **Type**: Array of strings
- **Description**: List of signal types to simulate
- **Options**: [Satellite Signals Reference](./SIGNALS.md)
- **Examples**: `["GPS_L1C"]`, `["GPS_L1C", "GALILEO_L1B"]`

### `mask_angle`

- **Type**: Float
- **Units**: Degrees
- **Description**: Elevation mask angle below which satellites are ignored
- **Example**: `10`
- **Notes**: Satellites below this angle are not used

### `transmit_eirp`

- **Type**: Float
- **Units**: dBW (decibels relative to one watt)
- **Description**: Effective Isotropic Radiated Power of satellite signals at transmission
- **Typical Values**:
  - GPS: ~27-30 dBW
- **Example**: `29.5`

### `cn0_attenuation`

- **Type**: Float
- **Units**: dB
- **Description**: Additional attenuation applied to carrier-to-noise ratio
- **Example**: `20`
- **Notes**: Higher values simulate weaker signal conditions (jamming, etc.)

## Complete Example

Here's a comprehensive configuration file example:

```toml
# General simulation parameters
initial_datetime = "2024-06-14T00:00:00-00:00"
duration = 7200  # [s] - 2 hours
fsim = 1         # [Hz] - 1 second resolution
trajectory_name = "road_finland_sdx_01_onego"

# Error modeling
rx_clock_type = "ocxo"
rx_noise = true
ionosphere = true
troposphere = false
pseudorange_awgn_sigma = 5.0   # [m]
doppler_awgn_sigma = 2.0       # [Hz]
carrier_phase_awgn_sigma = 0.2 # [cycles]

# GPS constellation
[[constellation]]
reference_constellation = "gps"
signals = ["gps_l1c"]
mask_angle = 10        # [deg]
transmit_eirp = 29.5   # [dBW]
cn0_attenuation = 20   # [dB]

# Galileo constellation (additional)
[[constellation]]
reference_constellation = "galileo"
signals = ["galileo_l1b", "galileo_l5q"]
mask_angle = 10        # [deg]
transmit_eirp = 31.0   # [dBW]
cn0_attenuation = 15   # [dB]
```

## Troubleshooting

### Common Configuration Errors

#### Missing Required Fields

```
ValueError: Missing required fields: {'initial_datetime', 'duration'}
```

**Solution**: Ensure all required fields are present in your TOML file.

#### Invalid TOML Syntax

```
tomli.TOMLDecodeError: Invalid value type at line X
```

**Solution**: Check TOML syntax, especially:

- String values must be quoted: `"value"`
- Arrays use square brackets: `["item1", "item2"]`
- Datetime format: `"YYYY-MM-DDTHH:MM:SS±TZ:TZ"`

#### Timezone Issues

The system automatically converts datetime to UTC, but ensure your initial datetime includes timezone information:

- **Correct**: `"2024-06-14T00:00:00+00:00"`
- **Incorrect**: `"2024-06-14T00:00:00"` (no timezone)

This guide should help you create and configure navsim simulations effectively.
