import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium
import branca.colormap as cm
from wacc_prediction import WaccPredictor

# Data Source for map: https://public.opendatasoft.com/explore/embed/dataset/world-administrative-boundaries-countries/table/

def display_map(df, technology):
    map = folium.Map(location=[10, 0], zoom_start=1, control_scale=True, scrollWheelZoom=True, tiles='CartoDB positron')
    
    if technology == "Solar PV":
        row = "solar_pv_wacc"
    elif technology == "Onshore Wind":
        row = "onshore_wacc"
    elif technology == "Offshore Wind":
        row = "offshore_wacc"

    choropleth = folium.Choropleth(
        geo_data='./DATA/country_boundaries.geojson',
        data=df,
        columns=('iso3_code', row),
        key_on='feature.properties.iso3_code',
        line_opacity=0.8,
        highlight=True,
        fill_color="YlGnBu",
        nan_fill_color = "grey",
        legend_name="Weighted Average Cost of Capital (%)"
    )
    choropleth.geojson.add_to(map)


    

    # Add the colorbar to the map
    #colormap = cm.linear.YlGnBu_09.scale(0, 20)
    #colormap.caption = 'Weighted Average Cost of Capital (%)' 
    #colormap.add_to(map)
    #choropleth.color_scale.width = 10

    df_indexed = df.set_index('iso3_code')
    df_indexed = df_indexed.dropna(subset="onshore_wacc")
    for feature in choropleth.geojson.data['features']:
        iso3_code = feature['properties']['iso3_code']
        feature['properties']['Solar WACC'] = (
        f"{df_indexed.loc[iso3_code, 'solar_pv_wacc']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']['Onshore Wind WACC'] = (
        f"{df_indexed.loc[iso3_code, 'onshore_wacc']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']['Offshore Wind WACC'] = (
        f"{df_indexed.loc[iso3_code, 'offshore_wacc']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        #feature['properties']['GDP'] = 'GDP: ' + '{:,}'.format(df_indexed.loc[country_name, 'State Pop'][0]) if country_name in list(df_indexed.index) else ''

    #choropleth.geojson.add_child(
        #folium.features.GeoJsonTooltip(['english_short'], labels=False)
    #)

    choropleth.geojson.add_child(
    folium.features.GeoJsonTooltip(
        fields=['english_short', 'Solar WACC', 'Onshore Wind WACC', 'Onshore Wind WACC'],  # Display these fields
        aliases=["Country:", "Solar PV:", "Onshore Wind\n:", "Offshore Wind:"],         # Display names for the fields
        localize=True,
        style="""
        background-color: #F0EFEF;
        border: 2px solid black;
        border-radius: 3px;
        box-shadow: 3px;
    """,
    max_width=400,
    )
)
    
    st_map = st_folium(map, width=700, height=350)

    country_name = ''
    if st_map['last_active_drawing']:
        country_name = st_map['last_active_drawing']['properties']['english_short']
    return country_name


country_waccs = pd.read_csv("./DATA/Country_Waccs_2024.csv")
print(country_waccs)


st.title("	🏦 Weighted Average Cost of Capital Forecaster (WACFOR)")
st.write(
    "Tool to estimate the cost of capital for renewable technologies\nV1.0 - Alpha\n")
tab1, tab2, tab3, tab4 = st.tabs(["🥇Global Estimates", "🌐 Map", "📈 Country Projections", "ℹ️ About"])

with tab1:
    st.header("Global Estimates")
with tab2:
    st.header("Map")
    option = st.selectbox(
        "Displayed Technology", ("Solar PV", "Onshore Wind", "Offshore Wind"), 
         index=0, placeholder="Select Technology...")
    display_map(country_waccs, option)
with tab3:
    st.header("Country Projections")
with tab4:
    text = open('about.md').read()
    st.write(text)
    

