# Supported Constellations

This document provides brief descriptions of the satellite constellations available for simulation in navsim.

## GNSS (Global Navigation Satellite Systems)

### GPS
Global Positioning System operated by the United States Space Force
- **Orbital Altitude**: ~20,200 km (MEO)
- **Ephemeris Format**: SP3
- **Number of Satellites**: ~32 operational satellites
- **Primary Purpose**: Global navigation and positioning
- **First Launch**: 1978

### Galileo
European Union's global navigation satellite system
- **Orbital Altitude**: ~23,222 km (MEO)
- **Ephemeris Format**: SP3
- **Number of Satellites**: ~30 satellites (constellation complete)
- **Primary Purpose**: Global navigation and positioning
- **First Launch**: 2005

### GLONASS
Russian global navigation satellite system
- **Orbital Altitude**: ~19,100 km (MEO)
- **Ephemeris Format**: SP3
- **Number of Satellites**: ~24 operational satellites
- **Primary Purpose**: Global navigation and positioning
- **First Launch**: 1982

### BeiDou
Chinese global navigation satellite system
- **Orbital Altitude**: ~21,500 km (MEO) for global satellites
- **Ephemeris Format**: SP3
- **Number of Satellites**: ~30+ satellites (including GEO and IGSO orbits)
- **Primary Purpose**: Global navigation and positioning
- **First Launch**: 2000

### QZSS
Quasi-Zenith Satellite System operated by Japan
- **Orbital Altitude**: ~32,000-40,000 km (highly elliptical and GEO orbits)
- **Ephemeris Format**: SP3
- **Number of Satellites**: 7 satellites planned
- **Primary Purpose**: Regional navigation augmentation for Asia-Oceania
- **First Launch**: 2010

## LEO Communication Constellations

### Iridium
Global satellite communication constellation
- **Orbital Altitude**: ~780 km (LEO - Low Earth Orbit)
- **Ephemeris Format**: TLE (Two-Line Elements)
- **Number of Satellites**: 75 satellites (66 operational + spares)
- **Primary Purpose**: Global satellite phone and data communication
- **Current Generation**: Iridium NEXT

### ORBCOMM
Machine-to-machine communication constellation
- **Orbital Altitude**: ~715-740 km (LEO)
- **Ephemeris Format**: TLE
- **Number of Satellites**: ~30 satellites
- **Primary Purpose**: IoT and M2M communications, asset tracking
- **Specialty**: Small data packet transmission

### Globalstar
Low Earth orbit satellite constellation for communications
- **Orbital Altitude**: ~1,414 km (LEO)
- **Ephemeris Format**: TLE
- **Number of Satellites**: ~48 satellites
- **Primary Purpose**: Satellite phone, low-speed data, and IoT services
- **Coverage**: Near-global (excluding polar regions)

### OneWeb
Global broadband internet constellation
- **Orbital Altitude**: ~1,200 km (LEO)
- **Ephemeris Format**: TLE
- **Number of Satellites**: 600+ satellites planned
- **Primary Purpose**: Global broadband internet access
- **Status**: Operational constellation being deployed

### Starlink
SpaceX's global broadband internet constellation
- **Orbital Altitude**: ~340-570 km (LEO), with some at ~1,150 km
- **Ephemeris Format**: TLE
- **Number of Satellites**: 5,000+ satellites (rapidly expanding)
- **Primary Purpose**: Global high-speed internet access
- **Notable Features**: Largest active satellite constellation

### Eutelsat
European satellite communication constellation (includes OneWeb)
- **Orbital Altitude**: Variable (LEO to GEO depending on specific satellites)
- **Ephemeris Format**: TLE
- **Number of Satellites**: Multiple satellites across different orbits
- **Primary Purpose**: Communication services, broadcasting, broadband
- **Note**: Includes both GEO and LEO assets

## Planned/Future Constellations

### Kuiper
Amazon's planned global broadband constellation
- **Orbital Altitude**: ~590-630 km (LEO)
- **Ephemeris Format**: TLE
- **Number of Satellites**: 3,236 satellites planned
- **Primary Purpose**: Global broadband internet access
- **Status**: In development, test satellites launched

### Qianfan
Chinese planned broadband internet constellation
- **Orbital Altitude**: ~1,145 km (LEO)
- **Ephemeris Format**: TLE
- **Number of Satellites**: 13,000+ satellites planned
- **Primary Purpose**: Global broadband internet access
- **Status**: Early development phase
- **Alternative Name**: Also known as "Thousand Sails"

## Technical Notes

- **SP3**: Standard format for precise satellite orbit and clock data, typically used for GNSS satellites
- **TLE**: Two-Line Element format containing orbital parameters for satellite tracking, commonly used for LEO satellites
- **MEO**: Medium Earth Orbit (2,000-35,786 km altitude)
- **LEO**: Low Earth Orbit (160-2,000 km altitude)
- **GEO**: Geostationary Earth Orbit (~35,786 km altitude)