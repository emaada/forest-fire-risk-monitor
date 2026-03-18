# Forest Fire Risk Monitor 

**Module:** `risk_scorer.py`  
**Based on:** Van Wagner & Pickett (1985) — Canadian Forest Fire Weather Index System

---

## Overview

This module is the risk engine for the Forest Fire Risk Monitor system. It calculates a **Fire Risk Index (FRI)** score for any geographic zone given its coordinates and vegetation dryness reading.

Output: a numeric score (0–100) and a categorical alert level (LOW → EXTREME).

This module is **standalone** — it does not depend on the backend, database, or frontend. The backend team can call `get_risk()` directly from their FastAPI endpoint.

---

## Quickstart

### Install dependencies
```bash
pip install httpx python-dotenv
```

### Run a test
```bash
python risk_scorer.py
```

Expected output:
```
{'temperature_c': 17.7, 'humidity_pct': 33, 'wind_kmh': 17.1, 'rain_mm': 0.0, 'fwi': 8.4, 'fri_score': 17.71, 'alert_level': 'LOW'}
```

### Call from another module
```python
import asyncio
from risk_scorer import get_risk

result = asyncio.run(get_risk(lat=37.5, lon=-119.5, ndvi=0.3))
print(result['alert_level'])  # LOW / MODERATE / HIGH / VERY_HIGH / EXTREME
```

---

## How It Works

The pipeline has four stages:

| Stage | What happens | Detail |
|-------|-------------|--------|
| 1 | Fetch weather | Calls Open-Meteo API with lat/lon. Returns max temperature, mean humidity, max wind speed, and precipitation sum for today. |
| 2 | Calculate FWI | Runs the 6-formula Canadian FWI chain: FFMC → DMC → DC → ISI → BUI → FWI. Returns a dimensionless fire danger number. |
| 3 | Compute FRI | Combines FWI (65% weight) with vegetation dryness from NDVI (35% weight) into a single 0–100 score. |
| 4 | Alert level | Buckets FRI into LOW / MODERATE / HIGH / VERY_HIGH / EXTREME using fixed thresholds. |

---

## The FWI System — Background

The **Fire Weather Index (FWI)** system was developed by C.E. Van Wagner and T.L. Pickett at the Petawawa National Forestry Institute, Canadian Forestry Service, published in Forestry Technical Report 33 (1985). It is the global standard for fire weather danger rating.

The system stacks six sub-indices:

| Index | Full name | Responds to | What it represents |
|-------|-----------|-------------|-------------------|
| FFMC | Fine Fuel Moisture Code | Same day | Dryness of surface litter. Controls ease of ignition. |
| DMC | Duff Moisture Code | Days–weeks | Dryness of the organic layer below the surface. |
| DC | Drought Code | Weeks–months | Deep soil drought. Persists even after rain. |
| ISI | Initial Spread Index | Wind + FFMC | Rate of fire spread. |
| BUI | Build-Up Index | DMC + DC | Total fuel available to burn. |
| FWI | Fire Weather Index | ISI + BUI | Final overall fire intensity index. Dimensionless. |

---

## Fire Risk Index (FRI) Score

FWI alone does not account for local vegetation state. The FRI score combines FWI with NDVI from your physical sensors:
```
FRI = (FWI_normalised × 0.65) + (vegetation_score × 0.35)
```

Where `vegetation_score = (1 − NDVI) / 2 × 100`.  
NDVI ranges from −1 (dry/bare) to +1 (dense green). This flips and rescales it so dry land produces a high danger score.

| FRI range | Alert level | Meaning |
|-----------|-------------|---------|
| 0 – 24 | LOW | Minimal fire danger. Normal conditions. |
| 25 – 49 | MODERATE | Some fire danger. Monitor conditions. |
| 50 – 69 | HIGH | Significant fire danger. Increased vigilance required. |
| 70 – 84 | VERY HIGH | Serious fire danger. Active monitoring and preparation. |
| 85 – 100 | EXTREME | Extreme fire danger. Immediate response consideration. |

---

## Function Reference

### `get_risk(lat, lon, ndvi)` — main entry point

| Parameter | Type | Description |
|-----------|------|-------------|
| `lat` | float | Latitude of the zone (WGS84 decimal degrees) |
| `lon` | float | Longitude of the zone (WGS84 decimal degrees) |
| `ndvi` | float | NDVI reading from sensor. Range: −1.0 (bare/dry) to +1.0 (dense green) |

**Returns:**
```python
{
    "temperature_c": float,   # max temp today from Open-Meteo
    "humidity_pct": float,    # mean humidity today
    "wind_kmh": float,        # max wind speed today
    "rain_mm": float,         # total precipitation today
    "fwi": float,             # computed Fire Weather Index
    "fri_score": float,       # final 0-100 Fire Risk Index
    "alert_level": str        # LOW / MODERATE / HIGH / VERY_HIGH / EXTREME
}
```

---

## Known Limitations

- **Previous day values:** The FWI system is stateful: FFMC, DMC, and DC should carry over from the previous day. Currently the module uses fixed starting defaults (FFMC=85, DMC=6, DC=15) on every run. The database team should store and pass previous day values for accurate multi-day operation.
- **Max temperature:** Uses daily maximum temperature, not current/live. This is correct per the FWI specification which is designed for noon standard time readings.
- **Canadian constants:** The FWI formula constants were derived from Canadian boreal forest conditions. Directionally accurate for other regions but may slightly over/underestimate for non-boreal vegetation.
- **NDVI source:** Must be provided by the caller from physical sensors. If unavailable, a fixed estimate (e.g. `0.4`) can be used temporarily.

---

## Data Sources

| Source | Data provided | Notes |
|--------|--------------|-------|
| Open-Meteo API | Temperature, humidity, wind, rain | Free, no API key required. `api.open-meteo.com/v1/forecast` |
| Physical IoT sensors | NDVI (vegetation dryness) | Provided by sensor team. Range −1 to +1. |

---

## File Structure
```
forest-fire-risk-monitor/
├── risk_scorer.py        ← this module (risk engine)
├── .env                  ← API keys (never commit)
├── .gitignore            ← excludes .env and cache
├── requirements.txt      ← pip dependencies
├── main.py               ← FastAPI app (backend team)
├── database/             ← DB models and connection (backend team)
└── frontend/             ← Next.js dashboard (frontend team)
```

---

## References

- Van Wagner, C.E. and Pickett, T.L. (1985). *Equations and FORTRAN Program for the Canadian Forest Fire Weather Index System.* Canadian Forestry Service, Forestry Technical Report 33. Ottawa 1985.
- Van Wagner, C.E. (1987). *Development and Structure of the Canadian Forest Fire Weather Index System.* Canadian Forestry Service, Forestry Technical Report 35.
- Open-Meteo (2024). *Weather Forecast API Documentation.* https://open-meteo.com/en/docs

---

*Forest Fire Risk Monitor — Risk Engine Module — Based on Van Wagner & Pickett (1985) Canadian FWI System*
