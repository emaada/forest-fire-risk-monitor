# Forest Fire Risk Monitor 

Calculates a Fire Risk Index (FRI) score for a geographic zone using the
Canadian FWI system (Van Wagner & Pickett, 1985) and Open-Meteo weather data.

## Setup
```bash
pip install httpx python-dotenv
```

## Usage
```python
import asyncio
from risk_scorer import get_risk

result = asyncio.run(get_risk(lat=37.5, lon=-119.5, ndvi=0.3))
print(result)
```

## Inputs

| Parameter | Type | Description |
|-----------|------|-------------|
| `lat` | float | Latitude (WGS84) |
| `lon` | float | Longitude (WGS84) |
| `ndvi` | float | Vegetation dryness from sensor (−1 to +1) |

## Data sources

- **Weather:** Open-Meteo API — `temperature_2m_max`, `relative_humidity_2m_mean`, `wind_speed_10m_max`, `precipitation_sum`
- **Vegetation:** NDVI from physical IoT sensor

## Reference

Van Wagner, C.E. & Pickett, T.L. (1985). *Equations and FORTRAN Program for the
Canadian Forest Fire Weather Index System.* Forestry Technical Report 33.
