
from __future__ import annotations
import numpy as np
import geopandas as gpd
import pandas as pd
import rasterio
from rasterstats import zonal_stats

METRICS = ["count","mean","min","max","std","percentile_10","percentile_90"]

def _custom_metrics(arr: np.ndarray, nodata=None, threshold: float | None = None) -> dict:
    # Custom metric: percent of pixels below a Tmin threshold (degC).
    result = {}
    if arr is None:
        return {"below_threshold_pct": np.nan}
    data = arr[~np.isnan(arr)]
    if data.size == 0:
        return {"below_threshold_pct": np.nan}
    if threshold is None:
        return {"below_threshold_pct": np.nan}
    result["below_threshold_pct"] = float((data < threshold).sum()) / float(data.size) * 100.0
    return result

def compute_zonal_stats(vector: gpd.GeoDataFrame, raster_path: str, band: int = 1, threshold: float | None = None) -> pd.DataFrame:
    # Compute zonal stats on a given band of a Tmin raster for each polygon in `vector`.
    with rasterio.open(raster_path) as src:
        nodata = src.nodata

    zs = zonal_stats(
        vectors=vector["geometry"],
        raster=raster_path,
        band=band,
        nodata=nodata,
        stats=METRICS,
        geojson_out=False,
        raster_out=False,
        all_touched=False
    )
    df = pd.DataFrame(zs)

    # Second pass to get custom metric using mini raster arrays
    zs_r = zonal_stats(
        vectors=vector["geometry"],
        raster=raster_path,
        band=band,
        nodata=nodata,
        stats=None,
        raster_out=True,
        all_touched=False
    )
    bt_list = []
    for item in zs_r:
        arr = item.get("mini_raster_array")
        if arr is None:
            bt_list.append(np.nan)
            continue
        a = arr.astype(float)
        if nodata is not None:
            a[a == nodata] = np.nan
        bt_list.append(_custom_metrics(a, nodata=nodata, threshold=threshold)["below_threshold_pct"])
    df["below_threshold_pct"] = bt_list
    return df

def attach_index(vector: gpd.GeoDataFrame, stats_df: pd.DataFrame, level: str) -> pd.DataFrame:
    meta_cols = []
    if "DEPARTAMENTO" in vector.columns: meta_cols.append("DEPARTAMENTO")
    if level in ("district","province"): 
        if "PROVINCIA_N" in vector.columns: meta_cols.append("PROVINCIA_N")
    if level == "district":
        if "DISTRITO_N" in vector.columns: meta_cols.append("DISTRITO_N")
    if "UBIGEO" in vector.columns: meta_cols.append("UBIGEO")

    out = pd.concat([vector.reset_index(drop=True)[meta_cols], stats_df], axis=1)
    return out
