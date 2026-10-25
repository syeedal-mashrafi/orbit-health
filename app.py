"""Orbit & Health — where is the ISS right now, and how healthy is the country below it?"""
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


def country_below(lat, lon):
    """Nearest country to a lat/lon point (offline lookup)."""
    cc = rg.search((lat, lon), mode=1)[0]["cc"]
    c = pycountry.countries.get(alpha_2=cc)
    return (c.name, c.alpha_3) if c else (cc, None)


@st.cache_data(ttl=86400)
def life_expectancy(iso3):
    """Life expectancy at birth (both sexes) from the WHO Global Health Observatory API."""
    url = f"https://ghoapi.azureedge.net/api/WHOSIS_000001?$filter=SpatialDim eq '{iso3}'"
    rows = requests.get(url, timeout=15).json().get("value", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df[df["Dim1"].astype(str).str.contains("BTSX")]  # both sexes
    df = df[["TimeDim", "NumericValue"]].rename(
        columns={"TimeDim": "Year", "NumericValue": "Life expectancy (years)"}
    )
    return df.sort_values("Year")


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
name, iso3 = country_below(lat, lon)
st.subheader(f"Nearest country below: {name}")
st.caption("When the ISS is over the ocean, this shows the closest country.")

if iso3:
    try:
        df = life_expectancy(iso3)
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        st.info("No WHO life expectancy data for this country.")
    else:
        latest = df.iloc[-1]
        st.metric("Life expectancy at birth", f"{latest.iloc[1]:.1f} years",
                  help=f"WHO, {int(latest.iloc[0])}")
        st.line_chart(df.set_index("Year"))

if st.button("🔄 Refresh position"):
    st.cache_data.clear()
    st.rerun()

st.caption("Data: wheretheiss.at · WHO Global Health Observatory")
