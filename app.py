# -*- coding: utf-8 -*-
"""
Aplicación Streamlit para el proyecto final de Programación en SIG.
Tema: Expropiaciones de la Ruta Nacional N.° 27.
Autor: Ervin López Espinoza
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium



# CONFIGURACIÓN GENERAL
st.set_page_config(
    page_title="Expropiaciones Ruta Nacional N.° 27",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Aplicación web SIG: Expropiaciones en la Ruta Nacional N.° 27")

st.markdown(
    """
    Esta aplicación presenta un análisis interactivo de datos asociados a procesos de
    expropiación vinculados con la **Ruta Nacional N.° 27**.

    La información incluye datos registrales, administrativos y espaciales, tales como:
    finca, plano catastrado, área registral, provincia, cantón, distrito, condición del trámite
    y coordenadas geográficas. Además, se incorpora una capa GeoJSON de distritos para
    contextualizar espacialmente los registros.
    """
)



# CARGA DE DATOS
URL_CSV = "https://raw.githubusercontent.com/Ervlopez/PROYECTO/main/Datos_Expropiacion-III.csv"
URL_GEOJSON = "https://raw.githubusercontent.com/Ervlopez/PROYECTO/main/distritos.geojson"



# CONFIGURACION DE DATOS

@st.cache_data
def cargar_datos():
    df = pd.read_csv(URL_CSV, encoding="latin1")

    # Corrección del nombre de columna por problema de codificación
    if "AÃ±o" in df.columns:
        df = df.rename(columns={"AÃ±o": "Año"})

    # Conversión segura de campos numéricos
    df["Area_re"] = pd.to_numeric(df["Area_re"], errors="coerce")
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longiud"] = pd.to_numeric(df["longiud"], errors="coerce")

    # Eliminar registros sin coordenadas válidas para el mapa
    df = df.dropna(subset=["latitud", "longiud"])

    return df


try:
    expropiaciones = cargar_datos()
except Exception as error:
    st.error(
        "No se pudieron cargar los datos. Revise que los archivos estén en el repositorio "
        "público de GitHub y que las URL raw sean correctas."
    )
    st.exception(error)
    st.stop()


# FILTROS INTERACTIVOS
st.sidebar.header("🔎 Filtros interactivos")

provincias = sorted(expropiaciones["Provincia"].dropna().unique())
provincia_sel = st.sidebar.multiselect(
    "Seleccione una o varias provincias:",
    options=provincias,
    default=provincias
)

condiciones = sorted(expropiaciones["condicion"].dropna().unique())
condicion_sel = st.sidebar.multiselect(
    "Seleccione la condición del trámite:",
    options=condiciones,
    default=condiciones
)

area_min = float(expropiaciones["Area_re"].min())
area_max = float(expropiaciones["Area_re"].max())


st.sidebar.markdown(f"**Registros seleccionados:** {len(datos_filtrados)}")


# INDICADORES GENERALES
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total de registros", len(datos_filtrados))

with col2:
    st.metric("Área total filtrada (m²)", f"{datos_filtrados['Area_re'].sum():,.2f}")

with col3:
    st.metric("Provincias seleccionadas", datos_filtrados["Provincia"].nunique())


# TABLA CON PANDAS
st.header("1. Tabla de datos filtrados")

st.markdown(
    """
    La siguiente tabla muestra los registros de expropiación filtrados según la provincia,
    condición del trámite y rango de área seleccionados en el panel lateral.
    """
)

columnas_mostrar = [
    "Identificador", "Finca", "Derechos", "Plano_cat", "Año",
    "Area_re", "Provincia", "Cantón", "Distrito", "condicion",
    "latitud", "longiud"
]

columnas_disponibles = [col for col in columnas_mostrar if col in datos_filtrados.columns]

st.dataframe(
    datos_filtrados[columnas_disponibles],
    use_container_width=True
)


# GRÁFICO ESTADÍSTICO CON PLOTLY
st.header("2. Gráfico estadístico")

st.markdown(
    """
    El gráfico resume el área registral total de los procesos de expropiación por provincia,
    tomando en cuenta únicamente los registros seleccionados mediante los filtros.
    """
)

if datos_filtrados.empty:
    st.warning("No hay datos disponibles con los filtros seleccionados.")
else:
    area_por_provincia = (
        datos_filtrados
        .groupby("Provincia", as_index=False)["Area_re"]
        .sum()
        .sort_values("Area_re", ascending=False)
    )

    fig = px.bar(
        area_por_provincia,
        x="Provincia",
        y="Area_re",
        text="Area_re",
        title="Área total de expropiación por provincia",
        labels={
            "Provincia": "Provincia",
            "Area_re": "Área registral total (m²)"
        }
    )

    fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
    fig.update_layout(xaxis_tickangle=-45)

    st.plotly_chart(fig, use_container_width=True)


# TABLA RESUMEN ADICIONAL
st.subheader("Resumen por condición del trámite")

st.markdown(
    """
    Esta tabla resume la cantidad de registros y el área total por condición del trámite.
    """
)

if not datos_filtrados.empty:
    # Se usa size() para contar registros sin depender de una columna específica
    # como "Identificador", ya que el nombre puede variar según el CSV.
    resumen_condicion = (
        datos_filtrados
        .groupby("condicion", as_index=False)
        .agg(area_total_m2=("Area_re", "sum"))
    )

    conteo_condicion = (
        datos_filtrados
        .groupby("condicion")
        .size()
        .reset_index(name="cantidad_registros")
    )

    resumen_condicion = (
        conteo_condicion
        .merge(resumen_condicion, on="condicion", how="left")
        .sort_values("cantidad_registros", ascending=False)
    )

    st.dataframe(resumen_condicion, use_container_width=True)


# MAPA INTERACTIVO CON FOLIUM
st.header("3. Mapa interactivo")

st.markdown(
    """
    El mapa muestra la ubicación espacial de los procesos de expropiación filtrados.
    Cada punto representa un registro y contiene información básica del trámite.
    """
)

if datos_filtrados.empty:
    st.warning("No hay registros para mostrar en el mapa.")
else:
    centro_lat = datos_filtrados["latitud"].mean()
    centro_lon = datos_filtrados["longiud"].mean()

    mapa = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=8,
        tiles="CartoDB positron"
    )

    # Capa de distritos
    folium.GeoJson(
        data=URL_GEOJSON,
        name="Distritos",
        style_function=lambda feature: {
            "fillOpacity": 0.05,
            "weight": 1
        }
    ).add_to(mapa)

    # Marcadores de expropiaciones organizados por condición.
    # Esto permite activar o desactivar cada condición desde el control de capas.
    colores_condicion = {
        "En trámite": "orange",
        "Finalizado": "green",
        "Finalizada": "green",
        "Concluido": "green",
        "Pendiente": "red",
    }

    condiciones_mapa = sorted(datos_filtrados["condicion"].dropna().unique())

    for condicion in condiciones_mapa:
        grupo_condicion = folium.FeatureGroup(
            name=f"Condición: {condicion}",
            show=True
        )

        datos_condicion = datos_filtrados[datos_filtrados["condicion"] == condicion]
        color_punto = colores_condicion.get(condicion, "blue")

        for _, registro in datos_condicion.iterrows():
            popup_html = f"""
            <b>Identificador:</b> {registro.get('Identificador', 'N/D')}<br>
            <b>Finca:</b> {registro.get('Finca', 'N/D')}<br>
            <b>Año:</b> {registro.get('Año', 'N/D')}<br>
            <b>Provincia:</b> {registro.get('Provincia', 'N/D')}<br>
            <b>Cantón:</b> {registro.get('Cantón', 'N/D')}<br>
            <b>Distrito:</b> {registro.get('Distrito', 'N/D')}<br>
            <b>Condición:</b> {registro.get('condicion', 'N/D')}<br>
            <b>Área registral:</b> {registro.get('Area_re', 0):,.2f} m²
            """

            folium.CircleMarker(
                location=[registro["latitud"], registro["longiud"]],
                radius=5,
                color=color_punto,
                fill=True,
                fill_color=color_punto,
                fill_opacity=0.7,
                weight=1,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{registro.get('Provincia', 'N/D')} - {registro.get('condicion', 'N/D')}"
            ).add_to(grupo_condicion)

        grupo_condicion.add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    st_folium(mapa, width=None, height=600)


# CONCLUSION
st.markdown("---")
st.markdown(
    """
    **Conclusión:** La aplicación permite integrar procesamiento de datos con pandas,
    visualización estadística con plotly y representación cartográfica con folium,
    cumpliendo con los elementos solicitados para el proyecto final.
    """
)
