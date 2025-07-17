from dataclasses import dataclass
from aspn23_lcm import type_satnav_satellite_system, type_satnav_signal_descriptor
from typing import List, Union


SIGNAL_DESCRIPTORS = {
    value: name.replace("SIGNAL_DESCRIPTOR_", "")
    for name, value in vars(type_satnav_signal_descriptor).items()
    if name.isupper()
}

SATELLITE_SYSTEMS = {
    value: name.replace("SATELLITE_SYSTEM_", "")
    for name, value in vars(type_satnav_satellite_system).items()
    if name.isupper()
}


@dataclass
class SatelliteSignal:
    received_power: float  # [dBW]
    fcarrier: float  # [Hz]
    modulation_type: str


@dataclass
class GnssSignal(SatelliteSignal):
    fchip: Union[float, List[float]]  # [chipping rate(s) - Hz]
    fdata: Union[float, List[float]]  # [data rate(s) - Hz]
    chip_sequence_length: Union[int, List[int]]  # [chips per sequence]


@dataclass
class LeoSatelliteSignal(SatelliteSignal):
    pass


# GPS Signals with RINEX Identifiers
GPS_L1C = GnssSignal(
    received_power=-160.0,  # Typical received power level [dBW]
    fcarrier=1575.42e6,
    modulation_type="BPSK",
    fchip=1.023e6,  # 1.023 MHz (C/A code only)
    fdata=50.0,  # 50 Hz navigation data rate
    chip_sequence_length=1023,  # C/A code length: 1023 chips, 1 ms period
)

GPS_L1P = GnssSignal(
    received_power=-163.0,  # Military signal
    fcarrier=1575.42e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # 10.23 MHz (P(Y) code only)
    fdata=50.0,
    chip_sequence_length=6187104000000,  # P(Y) code: ~6.19e12 chips (267 days)
)

GPS_L1L = GnssSignal(
    received_power=-157.0,  # Improved signal strength
    fcarrier=1575.42e6,
    modulation_type="MBOC",  # Multiplexed Binary Offset Carrier
    fchip=[1.023e6, 1.023e6],  # L1C-D and L1C-P components
    fdata=[25.0, 0.0],  # Data channel at 25 Hz, pilot channel has no data
    chip_sequence_length=[10230, 10230],  # Both 10 ms sequences
)

GPS_L2C = GnssSignal(
    received_power=-160.0,  # Civil signal
    fcarrier=1227.60e6,
    modulation_type="BPSK",
    fchip=[1.023e6, 1.023e6],  # L2C-L and L2C-M components
    fdata=[0.0, 25.0],  # L2C-L is pilot (no data), L2C-M has 25 Hz data
    chip_sequence_length=[767250, 10230],  # L2C-L: 750 ms, L2C-M: 10 ms
)

GPS_L2P = GnssSignal(
    received_power=-163.0,  # Military signal
    fcarrier=1227.60e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # 10.23 MHz (P(Y) code only)
    fdata=50.0,
    chip_sequence_length=6187104000000,  # P(Y) code: ~6.19e12 chips (267 days)
)

GPS_L5I = GnssSignal(
    received_power=-157.0,  # Higher power than L1
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # L5-I (data) component
    fdata=1000.0,  # L5-I has 1000 Hz data
    chip_sequence_length=10230,  # L5-I: 1 ms
)

GPS_L5Q = GnssSignal(
    received_power=-157.0,  # Higher power than L1
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # L5-Q (pilot) component
    fdata=0.0,  # L5-Q is pilot
    chip_sequence_length=102300,  # L5-Q: 10 ms
)

# GLONASS Signals with RINEX Identifiers
GLONASS_L1C = GnssSignal(
    received_power=-161.0,  # Typical GLONASS received power
    fcarrier=1602.0e6,  # Center frequency (FDMA varies by satellite)
    modulation_type="BPSK",
    fchip=511e3,  # 511 kHz
    fdata=50.0,
    chip_sequence_length=511,  # 1 ms sequence
)

GLONASS_L1P = GnssSignal(
    received_power=-165.0,  # Military signal
    fcarrier=1602.0e6,
    modulation_type="BPSK",
    fchip=5.11e6,  # 5.11 MHz
    fdata=50.0,
    chip_sequence_length=5110000,  # 1 second sequence
)

GLONASS_L2C = GnssSignal(
    received_power=-167.0,  # Lower power on L2
    fcarrier=1246.0e6,
    modulation_type="BPSK",
    fchip=511e3,  # 511 kHz
    fdata=50.0,
    chip_sequence_length=511,  # 1 ms sequence
)

GLONASS_L2P = GnssSignal(
    received_power=-170.0,  # Military signal, lower power
    fcarrier=1246.0e6,
    modulation_type="BPSK",
    fchip=5.11e6,  # 5.11 MHz
    fdata=50.0,
    chip_sequence_length=5110000,  # 1 second sequence
)

GLONASS_L3I = GnssSignal(
    received_power=-163.0,  # CDMA signal
    fcarrier=1202.025e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # 10.23 MHz
    fdata=1000.0,
    chip_sequence_length=10230,  # 1 ms sequence
)

# Galileo Signals with RINEX Identifiers
GALILEO_L1B = GnssSignal(
    received_power=-157.0,  # Open Service - E1-B (data)
    fcarrier=1575.42e6,
    modulation_type="CBOC",  # Composite Binary Offset Carrier
    fchip=1.023e6,  # E1-B component
    fdata=250.0,  # E1-B has data
    chip_sequence_length=4092,  # 4 ms sequence
)

GALILEO_L1C = GnssSignal(
    received_power=-157.0,  # Open Service - E1-C (pilot)
    fcarrier=1575.42e6,
    modulation_type="CBOC",  # Composite Binary Offset Carrier
    fchip=1.023e6,  # E1-C component
    fdata=0.0,  # E1-C is pilot
    chip_sequence_length=4092,  # 4 ms sequence
)

GALILEO_L5I = GnssSignal(
    received_power=-155.0,  # Higher power - E5a-I (data)
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # E5a-I component
    fdata=25.0,  # E5a-I has data
    chip_sequence_length=10230,  # E5a-I: 1 ms
)

GALILEO_L5Q = GnssSignal(
    received_power=-155.0,  # Higher power - E5a-Q (pilot)
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # E5a-Q component
    fdata=0.0,  # E5a-Q is pilot
    chip_sequence_length=102300,  # E5a-Q: 10 ms
)

GALILEO_L7I = GnssSignal(
    received_power=-155.0,  # Higher power - E5b-I (data)
    fcarrier=1207.14e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # E5b-I component
    fdata=125.0,  # E5b-I has data
    chip_sequence_length=10230,  # E5b-I: 1 ms
)

GALILEO_L7Q = GnssSignal(
    received_power=-155.0,  # Higher power - E5b-Q (pilot)
    fcarrier=1207.14e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # E5b-Q component
    fdata=0.0,  # E5b-Q is pilot
    chip_sequence_length=102300,  # E5b-Q: 10 ms
)

GALILEO_L8I = GnssSignal(
    received_power=-153.0,  # AltBOC - highest power - E5(a+b)-I
    fcarrier=1191.795e6,
    modulation_type="AltBOC",  # Alternative Binary Offset Carrier
    fchip=10.23e6,  # Combined E5 data
    fdata=25.0,  # Combined data rate
    chip_sequence_length=10230,  # 1 ms
)

GALILEO_L8Q = GnssSignal(
    received_power=-153.0,  # AltBOC - highest power - E5(a+b)-Q
    fcarrier=1191.795e6,
    modulation_type="AltBOC",  # Alternative Binary Offset Carrier
    fchip=10.23e6,  # Combined E5 pilot
    fdata=0.0,  # Pilot
    chip_sequence_length=102300,  # 10 ms
)

GALILEO_L6B = GnssSignal(
    received_power=-158.0,  # Commercial Service - E6-B (data)
    fcarrier=1278.75e6,
    modulation_type="BPSK",
    fchip=5.115e6,  # 5.115 MHz
    fdata=1000.0,
    chip_sequence_length=5115,  # 1 ms sequence
)

GALILEO_L6C = GnssSignal(
    received_power=-158.0,  # Commercial Service - E6-C (pilot)
    fcarrier=1278.75e6,
    modulation_type="BPSK",
    fchip=5.115e6,  # 5.115 MHz
    fdata=0.0,  # Pilot
    chip_sequence_length=5115,  # 1 ms sequence
)

# BeiDou Signals with RINEX Identifiers
BEIDOU_L2I = GnssSignal(
    received_power=-163.0,  # Regional service - B1I
    fcarrier=1561.098e6,
    modulation_type="BPSK",
    fchip=2.046e6,  # 2.046 MHz
    fdata=50.0,
    chip_sequence_length=2046,  # 1 ms sequence
)

BEIDOU_L1D = GnssSignal(
    received_power=-158.0,  # Global service - B1C data
    fcarrier=1575.42e6,
    modulation_type="MBOC",
    fchip=1.023e6,
    fdata=100.0,
    chip_sequence_length=10230,  # 10 ms sequence
)

BEIDOU_L1P = GnssSignal(
    received_power=-158.0,  # Global service - B1C pilot
    fcarrier=1575.42e6,
    modulation_type="MBOC",
    fchip=1.023e6,
    fdata=0.0,  # Pilot
    chip_sequence_length=10230,  # 10 ms sequence
)

BEIDOU_L7I = GnssSignal(
    received_power=-163.0,  # Regional service - B2I
    fcarrier=1207.14e6,
    modulation_type="BPSK",
    fchip=2.046e6,  # 2.046 MHz
    fdata=50.0,
    chip_sequence_length=2046,  # 1 ms sequence
)

BEIDOU_L5D = GnssSignal(
    received_power=-158.0,  # Global service - B2a data
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # 10.23 MHz
    fdata=100.0,
    chip_sequence_length=10230,  # 1 ms sequence
)

BEIDOU_L5P = GnssSignal(
    received_power=-158.0,  # Global service - B2a pilot
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # 10.23 MHz
    fdata=0.0,  # Pilot
    chip_sequence_length=10230,  # 1 ms sequence
)

BEIDOU_L7D = GnssSignal(
    received_power=-158.0,  # Global service - B2b data
    fcarrier=1207.14e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # 10.23 MHz
    fdata=100.0,
    chip_sequence_length=10230,  # 1 ms sequence
)

BEIDOU_L7P = GnssSignal(
    received_power=-158.0,  # Global service - B2b pilot
    fcarrier=1207.14e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # 10.23 MHz
    fdata=0.0,  # Pilot
    chip_sequence_length=10230,  # 1 ms sequence
)

BEIDOU_L6I = GnssSignal(
    received_power=-163.0,  # Regional service - B3I
    fcarrier=1268.52e6,
    modulation_type="BPSK",
    fchip=10.23e6,  # 10.23 MHz
    fdata=50.0,
    chip_sequence_length=10230,  # 1 ms sequence
)

# QZSS Signals with RINEX Identifiers (Japanese)
QZSS_L1C = GnssSignal(
    received_power=-160.0,  # GPS-compatible
    fcarrier=1575.42e6,
    modulation_type="BPSK",
    fchip=1.023e6,
    fdata=50.0,
    chip_sequence_length=1023,  # Same as GPS C/A
)

QZSS_L1L = GnssSignal(
    received_power=-157.0,  # GPS-compatible L1C
    fcarrier=1575.42e6,
    modulation_type="MBOC",
    fchip=1.023e6,
    fdata=25.0,
    chip_sequence_length=10230,  # 10 ms sequence
)

QZSS_L1S = GnssSignal(
    received_power=-158.0,  # QZSS-specific
    fcarrier=1575.42e6,
    modulation_type="BPSK",
    fchip=1.023e6,
    fdata=250.0,
    chip_sequence_length=4092,  # 4 ms sequence
)

QZSS_L2C = GnssSignal(
    received_power=-160.0,  # GPS-compatible
    fcarrier=1227.60e6,
    modulation_type="BPSK",
    fchip=1.023e6,
    fdata=25.0,
    chip_sequence_length=10230,  # Same as GPS L2C-M
)

QZSS_L5I = GnssSignal(
    received_power=-157.0,  # GPS-compatible L5-I
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=10.23e6,
    fdata=1000.0,
    chip_sequence_length=10230,  # 1 ms sequence
)

QZSS_L5Q = GnssSignal(
    received_power=-157.0,  # GPS-compatible L5-Q
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=10.23e6,
    fdata=0.0,  # Pilot
    chip_sequence_length=10230,  # 1 ms sequence
)

QZSS_L6D = GnssSignal(
    received_power=-158.0,  # LEX signal data
    fcarrier=1278.75e6,
    modulation_type="BPSK",
    fchip=5.115e6,
    fdata=2000.0,
    chip_sequence_length=5115,  # 1 ms sequence
)

QZSS_L6E = GnssSignal(
    received_power=-158.0,  # LEX signal pilot
    fcarrier=1278.75e6,
    modulation_type="BPSK",
    fchip=5.115e6,
    fdata=0.0,  # Pilot
    chip_sequence_length=5115,  # 1 ms sequence
)

# NavIC/IRNSS Signals with RINEX Identifiers (Indian)
NAVIC_L5A = GnssSignal(
    received_power=-158.0,  # Standard service
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=1.023e6,
    fdata=50.0,
    chip_sequence_length=1023,  # 1 ms sequence
)

NAVIC_L9A = GnssSignal(
    received_power=-158.0,  # Standard service
    fcarrier=2492.028e6,
    modulation_type="BPSK",
    fchip=1.023e6,
    fdata=50.0,
    chip_sequence_length=1023,  # 1 ms sequence
)

# SBAS Signals with RINEX Identifiers (Augmentation systems)
SBAS_L1C = GnssSignal(
    received_power=-158.0,  # Augmentation signal
    fcarrier=1575.42e6,
    modulation_type="BPSK",
    fchip=1.023e6,
    fdata=250.0,
    chip_sequence_length=1023,  # Same as GPS C/A
)

SBAS_L5I = GnssSignal(
    received_power=-158.0,  # Augmentation signal
    fcarrier=1176.45e6,
    modulation_type="BPSK",
    fchip=10.23e6,
    fdata=250.0,
    chip_sequence_length=10230,  # 1 ms sequence
)

# LEO Satellite Constellation Signals (Downlink Only)
# Globalstar (Voice/Data)
GLOBALSTAR_S = LeoSatelliteSignal(
    received_power=-120.0,  # S-band downlink
    fcarrier=2483.5e6,  # 2483.5-2500 MHz downlink
    modulation_type="CDMA",
)

# Iridium
IRIDIUM_L = LeoSatelliteSignal(
    received_power=-116.0,  # Improved power vs original
    fcarrier=1616.0e6,  # 1616-1626.5 MHz downlink
    modulation_type="TDMA/FDMA",
)

# OneWeb
ONEWEB_KU = LeoSatelliteSignal(
    received_power=-108.0,  # Ku-band downlink
    fcarrier=11.7e9,  # 11.7-12.7 GHz downlink
    modulation_type="OFDM",
)

# Orbcomm (IoT)
ORBCOMM_UHF = LeoSatelliteSignal(
    received_power=-120.0,  # UHF downlink
    fcarrier=137.0e6,  # 137-138 MHz downlink
    modulation_type="BPSK",
)

# Starlink
STARLINK_KU = LeoSatelliteSignal(
    received_power=-110.0,  # Ku-band downlink
    fcarrier=12.2e9,  # 12.2-12.7 GHz downlink
    modulation_type="OFDM",
)

# Amazon Kuiper
KUIPER_KU = LeoSatelliteSignal(
    received_power=-108.0,  # Ku-band downlink
    fcarrier=12.2e9,  # 12.2-12.7 GHz downlink
    modulation_type="OFDM",
)

# Qianfan (China)
QIANFAN_KU = LeoSatelliteSignal(
    received_power=-109.0,  # Ku-band downlink
    fcarrier=12.2e9,  # 12.2-12.7 GHz downlink
    modulation_type="OFDM",
)

# Eutelsat OneWeb (Post-merger)
EUTELSAT_ONEWEB_KU = LeoSatelliteSignal(
    received_power=-108.0,  # Ku-band downlink
    fcarrier=11.7e9,  # 11.7-12.7 GHz downlink
    modulation_type="OFDM",
)

SATELLITE_SIGNALS = {
    # GPS Signals
    "GPS_L1C": GPS_L1C,
    "GPS_L1P": GPS_L1P,
    "GPS_L1L": GPS_L1L,
    "GPS_L2C": GPS_L2C,
    "GPS_L2P": GPS_L2P,
    "GPS_L5I": GPS_L5I,
    "GPS_L5Q": GPS_L5Q,
    # GLONASS Signals
    "GLONASS_L1C": GLONASS_L1C,
    "GLONASS_L1P": GLONASS_L1P,
    "GLONASS_L2C": GLONASS_L2C,
    "GLONASS_L2P": GLONASS_L2P,
    "GLONASS_L3I": GLONASS_L3I,
    # Galileo Signals
    "GALILEO_L1B": GALILEO_L1B,
    "GALILEO_L1C": GALILEO_L1C,
    "GALILEO_L5I": GALILEO_L5I,
    "GALILEO_L5Q": GALILEO_L5Q,
    "GALILEO_L7I": GALILEO_L7I,
    "GALILEO_L7Q": GALILEO_L7Q,
    "GALILEO_L8I": GALILEO_L8I,
    "GALILEO_L8Q": GALILEO_L8Q,
    "GALILEO_L6B": GALILEO_L6B,
    "GALILEO_L6C": GALILEO_L6C,
    # BeiDou Signals
    "BEIDOU_L2I": BEIDOU_L2I,
    "BEIDOU_L1D": BEIDOU_L1D,
    "BEIDOU_L1P": BEIDOU_L1P,
    "BEIDOU_L7I": BEIDOU_L7I,
    "BEIDOU_L5D": BEIDOU_L5D,
    "BEIDOU_L5P": BEIDOU_L5P,
    "BEIDOU_L7D": BEIDOU_L7D,
    "BEIDOU_L7P": BEIDOU_L7P,
    "BEIDOU_L6I": BEIDOU_L6I,
    # QZSS Signals (Japanese)
    "QZSS_L1C": QZSS_L1C,
    "QZSS_L1L": QZSS_L1L,
    "QZSS_L1S": QZSS_L1S,
    "QZSS_L2C": QZSS_L2C,
    "QZSS_L5I": QZSS_L5I,
    "QZSS_L5Q": QZSS_L5Q,
    "QZSS_L6D": QZSS_L6D,
    "QZSS_L6E": QZSS_L6E,
    # NavIC/IRNSS Signals (Indian)
    "NAVIC_L5A": NAVIC_L5A,
    "NAVIC_L9A": NAVIC_L9A,
    # SBAS Signals
    "SBAS_L1C": SBAS_L1C,
    "SBAS_L5I": SBAS_L5I,
    # LEO Satellite Constellation Signals
    "GLOBALSTAR_S": GLOBALSTAR_S,
    "IRIDIUM_L": IRIDIUM_L,
    "ONEWEB_KU": ONEWEB_KU,
    "ORBCOMM_UHF": ORBCOMM_UHF,
    "STARLINK_KU": STARLINK_KU,
    "KUIPER_KU": KUIPER_KU,
    "QIANFAN_KU": QIANFAN_KU,
    "EUTELSAT_ONEWEB_KU": EUTELSAT_ONEWEB_KU,
}
