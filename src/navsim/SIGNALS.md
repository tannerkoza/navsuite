# Satellite Signals Reference

## GNSS (Global Navigation Satellite System) Signals

### GPS Signals
- **GPS_L1C** - L1 C/A Code (1575.42 MHz)
- **GPS_L1P** - L1 P(Y) Code (1575.42 MHz)
- **GPS_L1L** - L1C Signal (1575.42 MHz)
- **GPS_L2C** - L2 Civil (1227.60 MHz)
- **GPS_L2P** - L2 P(Y) Code (1227.60 MHz)
- **GPS_L5I** - L5 In-phase (1176.45 MHz)
- **GPS_L5Q** - L5 Quadrature (1176.45 MHz)

### GLONASS Signals (Russian)
- **GLONASS_L1C** - L1 Civil (1602.0 MHz)
- **GLONASS_L1P** - L1 Precision (1602.0 MHz)
- **GLONASS_L2C** - L2 Civil (1246.0 MHz)
- **GLONASS_L2P** - L2 Precision (1246.0 MHz)
- **GLONASS_L3I** - L3 CDMA (1202.025 MHz)

### Galileo Signals (European)
- **GALILEO_L1B** - E1-B Data (1575.42 MHz)
- **GALILEO_L1C** - E1-C Pilot (1575.42 MHz)
- **GALILEO_L5I** - E5a-I Data (1176.45 MHz)
- **GALILEO_L5Q** - E5a-Q Pilot (1176.45 MHz)
- **GALILEO_L7I** - E5b-I Data (1207.14 MHz)
- **GALILEO_L7Q** - E5b-Q Pilot (1207.14 MHz)
- **GALILEO_L8I** - E5(a+b)-I AltBOC (1191.795 MHz)
- **GALILEO_L8Q** - E5(a+b)-Q AltBOC (1191.795 MHz)
- **GALILEO_L6B** - E6-B Data (1278.75 MHz)
- **GALILEO_L6C** - E6-C Pilot (1278.75 MHz)

### BeiDou Signals (Chinese)
- **BEIDOU_L2I** - B1I Regional (1561.098 MHz)
- **BEIDOU_L1D** - B1C Data Global (1575.42 MHz)
- **BEIDOU_L1P** - B1C Pilot Global (1575.42 MHz)
- **BEIDOU_L7I** - B2I Regional (1207.14 MHz)
- **BEIDOU_L5D** - B2a Data Global (1176.45 MHz)
- **BEIDOU_L5P** - B2a Pilot Global (1176.45 MHz)
- **BEIDOU_L7D** - B2b Data Global (1207.14 MHz)
- **BEIDOU_L7P** - B2b Pilot Global (1207.14 MHz)
- **BEIDOU_L6I** - B3I Regional (1268.52 MHz)

### QZSS Signals (Japanese Regional)
- **QZSS_L1C** - L1 C/A Compatible (1575.42 MHz)
- **QZSS_L1L** - L1C Compatible (1575.42 MHz)
- **QZSS_L1S** - L1 SAIF (1575.42 MHz)
- **QZSS_L2C** - L2C Compatible (1227.60 MHz)
- **QZSS_L5I** - L5-I Compatible (1176.45 MHz)
- **QZSS_L5Q** - L5-Q Compatible (1176.45 MHz)
- **QZSS_L6D** - LEX Data (1278.75 MHz)
- **QZSS_L6E** - LEX Pilot (1278.75 MHz)

### NavIC/IRNSS Signals (Indian Regional)
- **NAVIC_L5A** - L5 Standard (1176.45 MHz)
- **NAVIC_L9A** - S-band Standard (2492.028 MHz)

### SBAS Signals (Satellite-Based Augmentation)
- **SBAS_L1C** - L1 Augmentation (1575.42 MHz)
- **SBAS_L5I** - L5 Augmentation (1176.45 MHz)

## LEO (Low Earth Orbit) Satellite Constellation Signals

### Communication & Data Services
- **GLOBALSTAR_S** - Voice/Data S-band (2483.5 MHz)
- **IRIDIUM_L** - Voice/Data L-band (1616.0 MHz)
- **ORBCOMM_UHF** - IoT Services (137.0 MHz)

### Broadband Internet Services
- **ONEWEB_KU** - Ku-band Broadband (11.7 GHz)
- **STARLINK_KU** - Ku-band Broadband (12.2 GHz)
- **KUIPER_KU** - Amazon Ku-band (12.2 GHz)
- **QIANFAN_KU** - Chinese Ku-band (12.2 GHz)
- **EUTELSAT_ONEWEB_KU** - Post-merger Ku-band (11.7 GHz)

## Summary
- **GNSS Signals**: 33 signals across 6 constellation systems (GPS, GLONASS, Galileo, BeiDou, QZSS, NavIC) plus SBAS augmentation
- **LEO Signals**: 8 signals across various communication and broadband internet services

### Frequency Bands Used
- **L1 Band (~1.5 GHz)**: Primary GNSS frequency, also used by some LEO systems
- **L2 Band (~1.2 GHz)**: Secondary GNSS frequency
- **L5 Band (~1.17 GHz)**: Modern GNSS signals with higher power
- **S Band (~2.4 GHz)**: Used by Globalstar and NavIC
- **UHF (~137 MHz)**: Used by Orbcomm
- **Ku Band (11-12 GHz)**: Primary frequency for LEO broadband services