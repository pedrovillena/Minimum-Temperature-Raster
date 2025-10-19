
from __future__ import annotations
import unicodedata
import re
import geopandas as gpd

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9\- _]", "", text).lower().strip()
    text = re.sub(r"[\s_]+", "-", text)
    return text

def normalize_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Normalize canonical admin columns if present (DEPARTAMEN, PROVINCIA, DISTRITO, UBIGEO).
    colmap = {c.lower(): c for c in gdf.columns}
    def best(*cands):
        for c in cands:
            if c.lower() in colmap:
                return colmap[c.lower()]
        return None

    dep = best("DEPARTAMEN","DEPARTAMENTO","NOMBDEP","DPTO","DEPA")
    prov = best("PROVINCIA","NOMBPROV","PROV")
    dist = best("DISTRITO","NOMBDIST","DIST")
    ubigeo = best("UBIGEO","IDDIST","UBI")

    def _upper(x):
        return x.astype(str).str.upper().str.normalize("NFKD").str.encode("ascii","ignore").str.decode("ascii")

    if dep and dep not in ("geometry",):
        gdf["DEPARTAMENTO"] = _upper(gdf[dep])
    else:
        gdf["DEPARTAMENTO"] = None
    if prov and prov not in ("geometry",):
        gdf["PROVINCIA_N"] = _upper(gdf[prov])
    else:
        gdf["PROVINCIA_N"] = None
    if dist and dist not in ("geometry",):
        gdf["DISTRITO_N"] = _upper(gdf[dist])
    else:
        gdf["DISTRITO_N"] = None

    if ubigeo and ubigeo not in ("geometry",):
        gdf["UBIGEO"] = gdf[ubigeo].astype(str).str.zfill(6).str[:6]
    else:
        iddpto = best("IDDPTO")
        idprov = best("IDPROV")
        iddist = best("IDDIST")
        if iddpto and idprov and iddist:
            gdf["UBIGEO"] = gdf[iddpto].astype(str).str.zfill(2) + gdf[idprov].astype(str).str.zfill(4).str[-2:] + gdf[iddist].astype(str).str.zfill(2).str[-2:]
        else:
            gdf["UBIGEO"] = None
    return gdf

def dissolve_level(gdf: gpd.GeoDataFrame, level: str) -> gpd.GeoDataFrame:
    level = level.lower()
    if level == "district":
        return gdf
    if level == "province":
        key = "PROVINCIA_N"
    elif level == "department":
        key = "DEPARTAMENTO"
    else:
        raise ValueError("level must be one of: district, province, department")
    cols = [c for c in ["DEPARTAMENTO","PROVINCIA_N","DISTRITO_N","UBIGEO"] if c in gdf.columns]
    dissolved = gdf[cols + ["geometry"]].dissolve(by=key, as_index=False, aggfunc="first")
    return dissolved
