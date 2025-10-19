
# Minimum-Temperature-Raster — Peru Tmin Zonal Stats + Policy + Streamlit

Public, reproducible template to compute zonal statistics from a Tmin GeoTIFF (Peru) by districts/provinces/departments, visualize risks, and draft public policy measures. Includes a Streamlit app.

## Environment
- Python 3.10+
- `requirements.txt` in repo root

## Data
- `data/DISTRITOS.shp` (+ sidecar files) — districts of Peru (WGS84 / EPSG:4326).
- `data/tmin_raster.tif` — Tmin raster. If multiband, band 1 = 2020, band 2 = 2021, ...

If files are large, remove them from the repo and let the app accept an upload instead.

## Structure
```
app/
  app.py
data/
  DISTRITOS.*
  tmin_raster.tif
  get_data.py
notebooks/
  estimation.ipynb
  eda_template.ipynb
src/
  utils.py
  zonal_stats.py
requirements.txt
README.md
```

## Run locally
```bash
pip install -r requirements.txt
streamlit run app/app.py
```

## Deploy (Streamlit Community Cloud)
1. Push this folder to a GitHub repo (e.g., `Minimum-Temperature-Raster`).
2. On Streamlit, create a new app pointing to `app/app.py` (Python 3.10).

## Zonal Metrics
- count, mean, min, max, std, percentile_10, percentile_90
- Custom: below_threshold_pct — percent of pixels with Tmin < X degC (user-defined)

## Map
Static choropleth (GeoPandas) rendered inside the app; export stats to CSV.

## Public Policy (guide)
Follows assignment guidance: High-Andean frost + Amazon friaje; includes 3 measures with objectives, targets, costs, KPIs.

## Notebooks
- `notebooks/estimation.ipynb` — starting point (copied from user-provided).
- `notebooks/eda_template.ipynb` — quick demo of the pipeline.
