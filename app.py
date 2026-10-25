"""Orbit & Health — where is the ISS right now, and how healthy is the country below it?"""
import math

import pandas as pd
import pycountry
import requests
import reverse_geocoder as rg
import streamlit as st

st.set_page_config(page_title="Orbit & Health", page_icon="🛰️")
st.title("🛰️ Orbit & Health")
st.caption("Where is the International Space Station right now, and how healthy is the country below it?")


@st.cache_data(ttl=10)
def iss_position():
    """Live ISS position from the Where the ISS At? API (no key needed)."""
    r = requests.get("https://api.wheretheiss.at/v1/satellites/25544", timeout=10)
    r.raise_for_status()
    d = r.json()
    return d["latitude"], d["longitude"], d["altitude"], d["velocity"]


# Territories that WHO reports under their parent country
PARENT = {
    "GF": "FR", "GP": "FR", "MQ": "FR", "RE": "FR", "YT": "FR", "PM": "FR",
    "BL": "FR", "MF": "FR", "NC": "FR", "PF": "FR", "WF": "FR",
    "PR": "US", "GU": "US", "VI": "US", "AS": "US", "MP": "US",
    "GL": "DK", "FO": "DK", "AW": "NL", "CW": "NL", "SX": "NL", "BQ": "NL",
    "BM": "GB", "KY": "GB", "VG": "GB", "TC": "GB", "MS": "GB", "AI": "GB",
    "GI": "GB", "FK": "GB", "SH": "GB", "IM": "GB", "JE": "GB", "GG": "GB",
    "HK": "CN", "MO": "CN", "EH": "MA",
}


def distance_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points."""
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def country_below(lat, lon):
    """Nearest country to a lat/lon point (offline lookup).

    Returns (place name, ISO3 code for WHO data, km to nearest town, data note).
    """
    hit = rg.search((lat, lon), mode=1)[0]
    km = distance_km(lat, lon, float(hit["lat"]), float(hit["lon"]))
    cc = hit["cc"]
    place = pycountry.countries.get(alpha_2=cc)
    name = place.name if place else cc
    parent = PARENT.get(cc)
    note = None
    if parent:
        p = pycountry.countries.get(alpha_2=parent)
        note = f"{name} is a territory, so this shows WHO data for {p.name}."
        return name, p.alpha_3, km, note
    return name, (place.alpha_3 if place else None), km, note


@st.cache_data(ttl=86400)
def life_expectancy(iso3):
    """Life expectancy at birth (both sexes) from the WHO Global Health Observatory API."""
    url = f"https://ghoapi.azureedge.net/api/WHOSIS_000001?$filter=SpatialDim eq '{iso3}'"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    rows = r.json().get("value", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df[df["Dim1"].astype(str).str.contains("BTSX")]  # both sexes
    df = df[["TimeDim", "NumericValue"]].rename(
        columns={"TimeDim": "Year", "NumericValue": "Life expectancy (years)"}
    )
    df = df.sort_values("Year")
    df["Year"] = df["Year"].astype(str)
    return df


# --- Space section ---
try:
    lat, lon, alt, vel = iss_position()
except Exception:
    st.error("Couldn't reach the ISS tracker. Try refreshing in a moment.")
    st.stop()

st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=1)
c1, c2, c3 = st.columns(3)
c1.metric("Latitude", f"{lat:.2f}°")
c2.metric("Longitude", f"{lon:.2f}°")
c3.metric("Speed", f"{vel:,.0f} km/h")
st.caption(f"Altitude: {alt:,.0f} km")

# --- Global health section ---
name, iso3, km, note = country_below(lat, lon)
if km > 300:
    st.subheader(f"Over the ocean · nearest country: {name}")
    st.caption(f"The ISS is about {km:,.0f} km from the nearest land.")
else:
    st.subheader(f"Flying over: {name}")
if note:
    st.caption(note)

if iso3:
    try:
        df = life_expectancy(iso3)
    except Exception:
        st.warning("Couldn't reach the WHO data service. Try refreshing in a moment.")
        df = None
    if df is None:
        pass
    elif df.empty:
        st.info("WHO has no life expectancy data for this country.")
    else:
        latest = df.iloc[-1]
        st.metric("Life expectancy at birth", f"{latest.iloc[1]:.1f} years",
                  help=f"WHO, {int(latest.iloc[0])}")
        st.line_chart(df.set_index("Year"))

if st.button("🔄 Refresh position"):
    st.cache_data.clear()
    st.rerun()

st.caption("Data: wheretheiss.at · WHO Global Health Observatory")
