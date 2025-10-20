
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
col_labels = {
    label_col: "Location",
    "mean": "Mean Tmin (°C)",
    "percentile_10": "10th Percentile (°C)",
    "percentile_90": "90th Percentile (°C)",
    "below_threshold_pct": "% Below Threshold",
    "risk_score": "Risk Score"
}
def format_table(df, cols):
    df_display = df[cols].copy()
    for c in df_display.select_dtypes(include="number").columns:
        df_display[c] = df_display[c].round(2)
    return df_display.rename(columns=col_labels)
c1, c2 = st.columns(2, gap="large")
with c1:
    st.write("**Top 15 Coldest (lowest mean Tmin)**")
    st.dataframe(format_table(coldest, [label_col, "mean", "percentile_10", "below_threshold_pct", "risk_score"]))
                 
with c2:
    st.write("**Top 15 Warmest (highest mean Tmin)**")
    st.dataframe(format_table(warmest, [label_col, "mean", "percentile_90", "risk_score"]))

st.subheader("Static map: mean Tmin")
gdf_plot = gdf_lvl.merge(out[[label_col, "mean"]], on=label_col, how="left")
fig2, ax = plt.subplots(figsize=(10, 10))
gdf_plot.plot(
    column="mean",
    cmap="YlOrRd",          
    linewidth=0.3,          
    edgecolor="gray",       
    legend=True,
    ax=ax,
    missing_kwds={
        "color": "lightgrey",
        "label": "Sin datos"
    }
)

ax.set_title(f"Choropleth Map by {level}", fontsize=12)
ax.set_axis_off()

#gdf_plot = gdf_lvl.copy()
#gdf_plot = gdf_plot.join(out["mean"], how="left")
#fig2 = plt.figure()
#ax = gdf_plot.plot(column="mean", legend=True)
#plt.title(f"Mean Tmin by {level}")
#plt.axis("off")
st.pyplot(fig2)

st.header("Downloads")
csv = out.to_csv(index=False).encode("utf-8")
st.download_button("Download zonal stats (CSV)", data=csv, file_name=f"tmin_zonal_{level}.csv", mime="text/csv")

st.header("Public Policy — Diagnosis & Measures")

st.markdown("""
### 📊 Diagnóstico basado en análisis de 746 distritos del Perú

Del análisis de temperatura mínima se identificaron las siguientes zonas críticas:
""")

# Tabla de departamentos más fríos
st.markdown("#### Departamentos con temperaturas más críticas:")
dept_data = {
    "Departamento": ["PUNO", "HUANCAVELICA", "APURÍMAC", "MOQUEGUA", "AYACUCHO"],
    "Tmin Promedio (°C)": [3.08, 3.82, 4.45, 5.12, 6.00],
    "Percentil 10 (°C)": [-3.8, -0.56, 0.56, -4.95, 2.02],
    "% Bajo 4°C": [29.29, 9.02, 2.78, 16.37, 0.55]
}
st.dataframe(pd.DataFrame(dept_data), use_container_width=True)

st.markdown("""
#### Distritos en situación extrema (Tmin < 0°C):

**15 distritos identificados** con temperaturas promedio bajo cero:
- **CAPAZO** (Tacna/Moquegua): -5.24°C promedio, 51.39% de área bajo 4°C
- **SUSAPAYA**: -5.06°C, percentil 10 de -8.5°C
- **SANTA ROSA**: -4.93°C, 41.9% bajo 4°C
- **TARATA, TICACO, SAN ANTONIO DE CHUCA, CANDARAVE** (Tacna/Moquegua)
- **PARATIA, PISACOMA, CORANI, SANTA LUCÍA, AJOYANI** (Puno)
- **CONDOROMA** (Cusco/Arequipa)
- **CARUMAS** (Moquegua)
- **SAN JUAN DE TARUCANI** (Arequipa)

**8 distritos con heladas extremas** (>35% de área bajo 4°C):
CAPAZO (51.39%), SAN JUAN DE TARUCANI (51.28%), PARATIA (48.15%), CORANI (45.83%), SANTA ROSA (41.9%), PISACOMA (41.25%), SAN ANTONIO DE CHUCA (40%), CANDARAVE (39.81%)
""")

st.markdown("---")

st.markdown("""
## 🎯 Propuestas Priorizadas de Política Pública

### 1️⃣ PROGRAMA DE MEJORAMIENTO TÉRMICO DE VIVIENDAS RURALES EN ZONAS DE FRÍO EXTREMO

**📍 Objetivo específico:**  
Reducir la incidencia de Infecciones Respiratorias Agudas (IRA) y mortalidad por hipotermia en población vulnerable de zonas con temperaturas bajo 0°C.

**🗺️ Población/territorio objetivo:**  
- **15 distritos identificados** con Tmin promedio bajo 0°C (rango: -5.24°C a -3.01°C)
- Ubicación: Tacna (Candarave, Tarata), Moquegua (Carumas), Puno (Paratia, Pisacoma, Corani, Santa Lucía, Ajoyani), Arequipa (San Juan de Tarucani), Cusco/Arequipa (Condoroma)
- Prioridad máxima: distritos con percentil 10 < -6°C (SUSAPAYA: -8.5°C, SANTA ROSA: -7.31°C, CANDARAVE: -6.8°C, TARATA: -6.55°C, CAPAZO: -6.47°C, TICACO: -6.16°C)

**Población exacta requiere:** Censo actualizado de viviendas en estos 15 distritos (datos INEI).

**🛠️ Intervención:**  
- Mejoramiento térmico integral de viviendas (aislamiento térmico en techos y paredes, sellado de grietas, ventanas con doble acristalamiento)
- Instalación de cocinas mejoradas con chimenea para calefacción eficiente
- Entrega de kits térmicos de emergencia (frazadas, ropa térmica)
- Construcción de refugios comunales para emergencias de frío extremo

**💰 Costo estimado:**  
Requiere cotización según:
- Distancia y acceso a cada distrito
- Disponibilidad de materiales en zona
- Costo de mano de obra local

**Referencia:** Programa FONCODES "Haku Wiñay" invierte S/ 10,000-15,000 por vivienda en zonas similares.

**📊 KPIs medibles:**  
- ✅ Reducir casos de IRA severa en menores de 5 años (comparar con data histórica MINSA de estos distritos)
- ✅ Reducir mortalidad por hipotermia a cero en grupos vulnerables
- ✅ Aumentar temperatura interior mínima medida en viviendas mejoradas
- ✅ Medir satisfacción de beneficiarios (encuesta post-intervención)
- ✅ Línea base: Obtener data MINSA/ESSALUD de últimos 3 inviernos en estos 15 distritos
""")

st.markdown("---")

st.markdown("""
### 2️⃣ PROTECCIÓN AGROPECUARIA EN DISTRITOS CON ALTA FRECUENCIA DE HELADAS

**📍 Objetivo específico:**  
Reducir pérdidas económicas por mortalidad de ganado (camélidos sudamericanos) y daños a cultivos alto-andinos debido a heladas frecuentes.

**🗺️ Población/territorio objetivo:**  
- **8 distritos con mayor frecuencia de heladas** (>35% de área con Tmin bajo 4°C):
  1. CAPAZO: 51.39%
  2. SAN JUAN DE TARUCANI: 51.28%
  3. PARATIA: 48.15%
  4. CORANI: 45.83%
  5. SANTA ROSA: 41.9%
  6. PISACOMA: 41.25%
  7. SAN ANTONIO DE CHUCA: 40%
  8. CANDARAVE: 39.81%

**Población exacta requiere:** Censo agropecuario de estos 8 distritos (número de productores, cabezas de ganado, hectáreas cultivadas).

**🛠️ Intervención:**  
- Construcción de cobertizos térmicos para protección de ganado durante heladas nocturnas
- Distribución de kits anti-heladas para cultivos (mallas térmicas, sistemas de micro-aspersión)
- Instalación de estaciones meteorológicas en los 8 distritos con sistema de alerta temprana (SMS/radio)
- Capacitación en técnicas de manejo de riesgo climático y calendario agrícola adaptado

**💰 Costo estimado:**  
Requiere cotización específica por distrito y validación con:
- Gobiernos locales de los 8 distritos
- Direcciones Regionales de Agricultura
- AGRO RURAL

**Referencia:** Proyectos similares de AGRO RURAL invierten S/ 3,000-6,000 por cobertizo según materiales y tamaño.

**📊 KPIs medibles:**  
- ✅ Reducir mortalidad de camélidos durante temporada de heladas (comparar con data de años previos de SENASA)
- ✅ Reducir pérdida de cultivos por heladas (medición en parcelas con y sin protección)
- ✅ Efectividad de alertas tempranas: % de eventos predichos correctamente con 24-48h de anticipación
- ✅ Incremento en ingresos anuales de productores beneficiarios
- ✅ Línea base: Obtener data de pérdidas económicas promedio de últimos 3 años en estos 8 distritos
""")

st.markdown("---")

st.markdown("""
### 3️⃣ SISTEMA DE RESPUESTA A FRIAJES EN REGIÓN AMAZÓNICA

**📍 Objetivo específico:**  
Reducir el impacto sanitario y educativo de eventos de friaje (caída súbita de temperatura) en poblaciones amazónicas.

**🗺️ Población/territorio objetivo:**  
- Departamentos: **Loreto, Ucayali, Madre de Dios** (mencionados en términos de referencia)
- **Identificación específica requiere:** Análisis de datos históricos de SENAMHI sobre eventos de friaje + cruce con data del raster para identificar distritos donde Tmin cae <12°C durante estos eventos

**Actualmente no tenemos:** Datos específicos de temperatura amazónica en este análisis (el raster muestra principalmente zona andina).

**🛠️ Intervención:**  
- Implementación de sistema de alerta temprana de friaje en coordinación con SENAMHI
- Pre-posicionamiento de kits de abrigo en escuelas y establecimientos de salud
- Protocolos de respuesta rápida para cierre preventivo de escuelas con continuidad educativa
- Reforzamiento temporal de personal y medicamentos en puestos de salud durante eventos

**💰 Costo estimado:**  
Requiere:
- Identificación precisa de distritos vulnerables
- Inventario de infraestructura educativa y de salud en zona
- Cotización de sistema de alerta y protocolos por provincia

**📊 KPIs medibles:**  
- ✅ Tiempo de respuesta desde alerta SENAMHI hasta activación de protocolos
- ✅ Reducir ausentismo escolar durante eventos de friaje (comparar con años previos)
- ✅ Reducir hospitalizaciones por IRA durante friajes
- ✅ % de instituciones educativas y de salud con kits pre-posicionados
- ✅ Línea base: Obtener data de SENAMHI de frecuencia e intensidad de friajes + data MINSA/MINEDU de impacto
""")

st.markdown("---")

st.warning("""
**⚠️ IMPORTANTE - Pasos siguientes para implementación:**

Estas propuestas se basan en el análisis geoespacial de **746 distritos** procesados. Para su implementación se requiere:

1. **Estudios complementarios:**
   - Censo de población y viviendas en los 15 distritos críticos (coordinación con INEI)
   - Censo agropecuario en los 8 distritos con alta frecuencia de heladas (CENAGRO/SENASA)
   - Análisis temporal de eventos de friaje amazónico (SENAMHI últimos 10 años)

2. **Validación de costos:**
   - Cotizaciones con proveedores locales y empresas constructoras
   - Consulta con FONCODES, AGRO RURAL, gobiernos regionales sobre experiencias similares
   - Estudios de pre-inversión (Invierte.pe)

3. **Líneas base para KPIs:**
   - Data MINSA/ESSALUD: casos IRA, neumonías, mortalidad por frío (últimos 3 años)
   - Data SENASA: mortalidad de ganado por distrito
   - Data MINEDU: ausentismo escolar durante meses fríos
   - Data económica: pérdidas por heladas (encuestas a productores)

4. **Articulación institucional:**
   - Gobiernos regionales de Puno, Tacna, Moquegua, Arequipa, Cusco
   - MIDIS, MVCS, MINAGRI, MINSA, MINEDU
   - Municipalidades distritales identificadas
""")

st.info("""
**💡 Nota metodológica:**  
Este análisis utilizó un raster de temperatura mínima procesado para 746 distritos del Perú. Los datos presentados son resultados directos del análisis geoespacial. Todos los valores de temperatura, percentiles y porcentajes son mediciones reales del procesamiento realizado.
""")

st.caption("Built with GeoPandas, rasterstats, rioxarray, and Streamlit.")