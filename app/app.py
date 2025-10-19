
import os
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils import normalize_columns, dissolve_level
from src.zonal_stats import compute_zonal_stats, attach_index

st.set_page_config(page_title="Peru Tmin — Zonal Stats", layout="wide")
st.title("Peru Minimum Temperature (Tmin) — Zonal Statistics & Policy Explorer")

st.sidebar.header("Data")
default_raster = "data/tmin_raster.tif" if os.path.exists("data/tmin_raster.tif") else None
uploaded_raster = st.sidebar.file_uploader("Upload GeoTIFF (Tmin)", type=["tif","tiff"])
raster_path = None
if uploaded_raster is not None:
    raster_path = "data/_uploaded.tif"
    with open(raster_path, "wb") as f:
        f.write(uploaded_raster.read())
elif default_raster:
    raster_path = default_raster
else:
    st.sidebar.warning("No raster found. Please upload a GeoTIFF.")
    st.stop()

shape_path = "data/DISTRITOS.shp"
if not os.path.exists(shape_path):
    st.error("Missing districts shapefile at data/DISTRITOS.shp")
    st.stop()

gdf = gpd.read_file(shape_path).to_crs("EPSG:4326")
gdf = normalize_columns(gdf)

level = st.sidebar.selectbox("Territorial level", ["district","province","department"], index=0)
thr = st.sidebar.number_input("Threshold for custom metric (Tmin < X degC)", value=0.0, step=0.5, format="%.1f")
band = st.sidebar.number_input("Raster band (1 = 2020, 2 = 2021, ...)", min_value=1, max_value=60, value=1, step=1)

if level != "district":
    gdf_lvl = dissolve_level(gdf, level)
else:
    gdf_lvl = gdf.copy()

st.sidebar.header("Filters")
min_pixels = st.sidebar.number_input("Min pixel count (quality filter)", value=10, step=1, min_value=0)

with st.spinner("Computing zonal statistics..."):
    zs = compute_zonal_stats(gdf_lvl, raster_path, band=int(band), threshold=float(thr))
    out = attach_index(gdf_lvl, zs, level=level)
    out = out[out["count"] >= min_pixels]

st.success(f"Computed stats for {len(out)} {level}s on band {band}.")

# Derived risk score example
out["risk_score"] = (100 - out["percentile_10"]).rank(pct=True) * 0.6 + out["below_threshold_pct"].rank(pct=True) * 0.4

st.header("Visualizations")
st.subheader("Distribution of mean Tmin")
fig1 = plt.figure()
plt.hist(out["mean"].dropna(), bins=40)
plt.xlabel("Mean Tmin (degC)")
plt.ylabel("Count")
plt.title(f"Distribution of mean Tmin — {level}")
st.pyplot(fig1)

st.subheader("Ranking: Coldest and Warmest")
label_col = "DISTRITO_N" if level=="district" else ("PROVINCIA_N" if level=="province" else "DEPARTAMENTO")
coldest = out.sort_values("mean").head(15)
warmest = out.sort_values("mean", ascending=False).head(15)
c1, c2 = st.columns(2, gap="large")
with c1:
    st.write("**Top 15 Coldest (lowest mean Tmin)**")
    st.dataframe(coldest[[label_col, "mean","percentile_10","below_threshold_pct","risk_score"]])
with c2:
    st.write("**Top 15 Warmest (highest mean Tmin)**")
    st.dataframe(warmest[[label_col, "mean","percentile_90","risk_score"]])

st.subheader("Static map: mean Tmin")
gdf_plot = gdf_lvl.copy()
gdf_plot = gdf_plot.join(out["mean"], how="left")
fig2 = plt.figure()
ax = gdf_plot.plot(column="mean", legend=True)
plt.title(f"Mean Tmin by {level}")
plt.axis("off")
st.pyplot(fig2)

st.header("Downloads")
csv = out.to_csv(index=False).encode("utf-8")
st.download_button("Download zonal stats (CSV)", data=csv, file_name=f"tmin_zonal_{level}.csv", mime="text/csv")

st.header("Public Policy — Diagnosis & Measures")
with st.expander("Diagnosis (auto-generated draft)"):
    st.markdown(
        "- High-Andean frost risk: Districts in Puno, Cusco, Ayacucho, Huancavelica, Pasco concentrate the lowest Tmin and highest % below threshold.\n"
        "- Amazon cold surges (friaje): Loreto, Ucayali, Madre de Dios may show sharp Tmin drops during surge months.\n"
        "- Prioritization rule: Focus districts with (a) percentile_10 <= 0–2 degC and (b) below_threshold_pct >= 20%."
    )

st.subheader("Prioritized measures (template)")
st.markdown(
    "1) **Thermal Housing & ISUR retrofits**  \n"
    "- Objective: Reduce ARI/ILI incidence among children <5 and elders.  \n"
    "- Target: High-Andean districts (<= p10 threshold).  \n"
    "- Intervention & Cost: S/ 6,000 per household (insulation + sealing + improved cookstove).  \n"
    "- KPI: -20% ARI cases (MINSA/ESSALUD) in 2 winters; +10% indoor Tmin vs baseline.\n\n"
    "2) **Livestock shelters + anti-frost kits**  \n"
    "- Objective: Cut alpaca/ovines mortality and crop frost loss.  \n"
    "- Target: Rural districts with >=30% pixels <0 degC.  \n"
    "- Intervention & Cost: S/ 2,500 per shelter; S/ 300 per anti-frost kit.  \n"
    "- KPI: -25% livestock mortality; -15% frost-related crop loss.\n\n"
    "3) **School calendar & Amazon 'friaje' response**  \n"
    "- Objective: Maintain attendance and reduce respiratory outbreaks during surges.  \n"
    "- Target: Amazon districts (Loreto/Ucayali/Madre de Dios) with recurrent Tmin <12 degC events.  \n"
    "- Intervention & Cost: S/ 50,000 per province (communication, shelters, PPE, blankets).  \n"
    "- KPI: -15% missed school days during surge months; response time <24h from alert."
)

st.caption("Built with GeoPandas, rasterstats, rioxarray, and Streamlit.")
