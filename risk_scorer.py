""" import httpx
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

async def fetch_fwi(lat: float, lon: float) -> dict:
    url = "https://api.openweathermap.org/data/2.5/fwi"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY
    }
    
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    
def normalize_fwi(raw_fwi: float) -> float:
    
    return min(raw_fwi, 100.0)

def compute_fri(fwi_raw: float, ndvi: float) -> float:
    
    fwi_score = normalize_fwi(fwi_raw)
    vegetation_score = (1 - ndvi) / 2 * 100
    return round(fwi_score * 0.65 + vegetation_score * 0.35, 2)


def get_alert_level(fri: float) -> str:
    
    if fri < 25: return "LOW"
    if fri < 50: return "MODERATE"
    if fri < 70: return "HIGH"
    if fri < 85: return "VERY_HIGH"
    return "EXTREME"

async def get_risk(lat: float, lon: float, ndvi: float):
   
    data = await fetch_fwi(lat, lon)
    fwi_today = data["list"][0]["main"]["fwi"]
    
    fri = compute_fri(fwi_today, ndvi)
    level = get_alert_level(fri)
    
    return {
        "fwi": fwi_today,
        "fri_score": fri,
        "alert_level": level
    }


if __name__ == "__main__":
    result = asyncio.run(get_risk(
        lat=37.5,
        lon=-119.5,
        ndvi=0.3
    ))
    print(result) """

import httpx
import asyncio
import math
from dotenv import load_dotenv
from datetime import datetime

# ─────────────────────────────────────────
# STEP 1: Fetch raw weather from Open-Meteo
# ─────────────────────────────────────────

async def fetch_weather(lat: float, lon: float) -> dict:
    """
    Fetch raw weather data from Open-Meteo API.

    Parameters:
    lat (float): latitude of location
    lon (float): longitude of location

    Returns:
    dict: JSON response from Open-Meteo API

    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,relative_humidity_2m_mean,wind_speed_10m_max,precipitation_sum",
        "wind_speed_unit": "kmh",
        "timezone": "UTC",
        "forecast_days": 1
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

# ─────────────────────────────────────────
# STEP 2: Compute FWI from raw weather
# ─────────────────────────────────────────
# Based on Canadian Forest Service FWI formulas
# Inputs: temp (°C), rh (%), wind (km/h), rain (mm)

def compute_ffmc(temp: float, rh: float, wind: float, rain: float, ffmc_prev: float = 85.0) -> float:
    
    """
    Compute the Fine Fuel Moisture Code (FFMC) from raw weather data.

    Parameters:
    temp (float): temperature in degrees Celsius
    rh (float): relative humidity in percent
    wind (float): wind speed in kilometers per hour
    rain (float): rainfall in millimeters
    ffmc_prev (float, optional): previous FFMC value, defaults to 85.0

    Returns:
    float: FFMC value
    """
    mo = 147.2 * (101 - ffmc_prev) / (59.5 + ffmc_prev)
    if rain > 0.5:
        rf = rain - 0.5
        if mo <= 150:
            mo += 42.5 * rf * math.exp(-100 / (251 - mo)) * (1 - math.exp(-6.93 / rf))
        else:
            mo += 42.5 * rf * math.exp(-100 / (251 - mo)) * (1 - math.exp(-6.93 / rf)) + 0.0015 * (mo - 150)**2 * rf**0.5
        mo = min(mo, 250)
    ed = 0.942 * rh**0.679 + 11 * math.exp((rh - 100) / 10) + 0.18 * (21.1 - temp) * (1 - math.exp(-0.115 * rh))
    ew = 0.618 * rh**0.753 + 10 * math.exp((rh - 100) / 10) + 0.18 * (21.1 - temp) * (1 - math.exp(-0.115 * rh))
    if mo > ed:
        kd = 0.424 * (1 - (rh / 100)**1.7) + 0.0694 * wind**0.5 * (1 - (rh / 100)**8)
        ko = kd * 0.581 * math.exp(0.0365 * temp)
        m = ed + (mo - ed) * 10**(-ko)
    elif mo < ew:
        kw = 0.424 * (1 - ((100 - rh) / 100)**1.7) + 0.0694 * wind**0.5 * (1 - ((100 - rh) / 100)**8)
        k1 = kw * 0.581 * math.exp(0.0365 * temp)
        m = ew - (ew - mo) * 10**(-k1)
    else:
        m = mo
    return 59.5 * (250 - m) / (147.2 + m)

def compute_dmc(temp: float, rh: float, rain: float, dmc_prev: float = 6.0, month: int = 6) -> float:
    """Duff Moisture Code — organic layer dryness."""
    day_length = [6.5,7.5,9.0,12.8,13.9,13.9,12.4,10.9,9.4,8.0,7.0,6.0]
    dl = day_length[month - 1]
    if rain > 1.5:
        re = 0.92 * rain - 1.27
        mo = 20 + math.exp(5.6348 - dmc_prev / 43.43)
        b = 100 / (0.5 + 0.3 * dmc_prev) if dmc_prev <= 33 else (14 - 1.3 * math.log(dmc_prev) if dmc_prev <= 65 else 6.2 * math.log(dmc_prev) - 17.2)
        mr = mo + 1000 * re / (48.77 + b * re)
        pr = 244.72 - 43.43 * math.log(mr - 20)
        dmc_prev = max(pr, 0)
    if temp > -1.1:
        k = 1.894 * (temp + 1.1) * (100 - rh) * dl * 1e-6
        return dmc_prev + 100 * k
    return dmc_prev

def compute_dc(temp: float, rain: float, dc_prev: float = 15.0, month: int = 6) -> float:
    """Drought Code — deep layer dryness."""
    lf = [-1.6,-1.6,-1.6,0.9,3.8,5.8,6.4,5.0,2.4,0.4,-1.6,-1.6]
    fl = lf[month - 1]
    if rain > 2.8:
        rd = 0.83 * rain - 1.27
        qo = 800 * math.exp(-dc_prev / 400)
        qr = qo + 3.937 * rd
        dr = 400 * math.log(800 / qr)
        dc_prev = max(dr, 0)
    if temp > -2.8:
        v = 0.36 * (temp + 2.8) + fl
        return dc_prev + 0.5 * max(v, 0)
    return dc_prev

def compute_isi(wind: float, ffmc: float) -> float:
    """Initial Spread Index — how fast fire spreads."""
    fm = 147.2 * (101 - ffmc) / (59.5 + ffmc)
    fw = math.exp(0.05039 * wind)
    ff = 91.9 * math.exp(-0.1386 * fm) * (1 + fm**5.31 / 4.93e7)
    return 0.208 * fw * ff

def compute_bui(dmc: float, dc: float) -> float:
    """Build-Up Index — total fuel available."""
    if dmc <= 0.4 * dc:
        return 0.8 * dmc * dc / (dmc + 0.4 * dc)
    else:
        return dmc - (1 - 0.8 * dc / (dmc + 0.4 * dc)) * (0.92 + (0.0114 * dmc)**1.7)

def compute_fwi(isi: float, bui: float) -> float:
    """Final Fire Weather Index."""
    if bui <= 80:
        fd = 0.626 * bui**0.809 + 2.0
    else:
        fd = 1000 / (25 + 108.64 * math.exp(-0.023 * bui))
    b = 0.1 * isi * fd
    if b > 1:
        return math.exp(2.72 * (0.434 * math.log(b))**0.647)
    return b

def calculate_fwi_from_weather(temp: float, rh: float, wind: float, rain: float, month: int) -> float:
    """Chain all FWI sub-indices together and return final FWI score."""
    ffmc = compute_ffmc(temp, rh, wind, rain)
    dmc  = compute_dmc(temp, rh, rain, month=month)
    dc   = compute_dc(temp, rain, month=month)
    isi  = compute_isi(wind, ffmc)
    bui  = compute_bui(dmc, dc)
    fwi  = compute_fwi(isi, bui)
    return round(fwi, 2)

# ─────────────────────────────────────────
# STEP 3: FRI scoring + alert level
# ─────────────────────────────────────────

def normalize_fwi(raw_fwi: float) -> float:
    return min(raw_fwi, 100.0)

def compute_fri(fwi_raw: float, ndvi: float) -> float:
    fwi_score = normalize_fwi(fwi_raw)
    vegetation_score = (1 - ndvi) / 2 * 100
    return round(fwi_score * 0.65 + vegetation_score * 0.35, 2)

def get_alert_level(fri: float) -> str:
    if fri < 25: return "LOW"
    if fri < 50: return "MODERATE"
    if fri < 70: return "HIGH"
    if fri < 85: return "VERY_HIGH"
    return "EXTREME"

# ─────────────────────────────────────────
# STEP 4: Main entry point
# ─────────────────────────────────────────

async def get_risk(lat: float, lon: float, ndvi: float) -> dict:
    data = await fetch_weather(lat, lon)
    daily = data["daily"]

    temp  = daily["temperature_2m_max"][0]
    rh    = daily["relative_humidity_2m_mean"][0]
    wind  = daily["wind_speed_10m_max"][0]
    rain  = daily["precipitation_sum"][0] or 0.0

    temp_curr = data["current"]["temperature_2m"]
    rh_curr   = data["current"]["relative_humidity_2m"]
    wind_curr = data["current"]["wind_speed_10m"]
    rain_curr = data["current"]["precipitation"]

    current_month = datetime.now().month

    fwi   = calculate_fwi_from_weather(temp, rh, wind, rain, month=current_month)
    fri   = compute_fri(fwi, ndvi)
    level = get_alert_level(fri)

    return {
        "temperature_c_curr": temp_curr,
        "humidity_pct_curr": rh_curr,
        "wind_kmh_curr": wind_curr,
        "rain_mm_curr": rain_curr,

        "temperature_c": temp,
        "humidity_pct": rh,
        "wind_kmh": wind,
        "rain_mm": rain,
        "fwi": fwi,
        "fri_score": fri,
        "alert_level": level
    }

if __name__ == "__main__":
    result = asyncio.run(get_risk(
        lat=37.7749,   # San Francisco
        lon=-122.4194,
        ndvi=0.3
    ))
    print(result)