import streamlit as st
import folium
import pandas as pd
import numpy as np
from streamlit_folium import st_folium
import branca.colormap as cm
from wacc_prediction import WaccPredictor
import altair as alt

# Data Source for map: https://public.opendatasoft.com/explore/embed/dataset/world-administrative-boundaries-countries/table/


# Call WaccPredictor Object
wacc_predictor = WaccPredictor(crp_data = "./DATA/CRPs.csv", 
generation_data="./DATA/Ember Yearly Data 2023.csv", GDP="./DATA/GDPPerCapita.csv",
tax_data="./DATA/TaxData.csv", ember_targets="./DATA/Ember_2030_Targets.csv", 
us_ir="./DATA/US_IR.csv")

def display_map(df, technology):
    map = folium.Map(location=[10, 0], zoom_start=1, control_scale=True, scrollWheelZoom=True, tiles='CartoDB positron')
    df = df.rename(columns={"Country code":"iso3_code"})

    choropleth = folium.Choropleth(
        geo_data='./DATA/country_boundaries.geojson',
        data=df,
        columns=('iso3_code', "WACC"),
        key_on='feature.properties.iso3_code',
        line_opacity=0.8,
        highlight=True,
        fill_color="YlGnBu",
        nan_fill_color = "grey",
        legend_name="Weighted Average Cost of Capital (%)"
    )
    choropleth.geojson.add_to(map)


    df_indexed = df.set_index('iso3_code')
    df_indexed = df_indexed.dropna(subset="WACC")
    for feature in choropleth.geojson.data['features']:
        iso3_code = feature['properties']['iso3_code']
        feature['properties'][technology + ' WACC'] = (
        f"{df_indexed.loc[iso3_code, 'WACC']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']["Debt_Share"] = (
        f"{df_indexed.loc[iso3_code, 'Debt_Share']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']["Equity_Cost"] = (
        f"{df_indexed.loc[iso3_code, 'Equity_Cost']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']["Debt_Cost"] = (
        f"{df_indexed.loc[iso3_code, 'Debt_Cost']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']["Tax_Rate"] = (
        f"{df_indexed.loc[iso3_code, 'Tax_Rate']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        #feature['properties']['GDP'] = 'GDP: ' + '{:,}'.format(df_indexed.loc[country_name, 'State Pop'][0]) if country_name in list(df_indexed.index) else ''

    #choropleth.geojson.add_child(
        #folium.features.GeoJsonTooltip(['english_short'], labels=False)
    #)

    choropleth.geojson.add_child(
    folium.features.GeoJsonTooltip(
        fields=['english_short', technology + ' WACC', "Equity_Cost", "Debt_Cost", "Debt_Share", "Tax_Rate"],  # Display these fields
        aliases=["Country:", technology + ":", "Cost of Equity:", "Cost of Debt:", "Debt Share:", "Tax_Rate"],         # Display names for the fields
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

@st.cache_data
def get_sorted_waccs(df, technology):

    if technology == "Solar PV":
        column = "solar_pv_wacc"
    elif technology == "Onshore Wind":
        column = "onshore_wacc"
    elif technology == "Offshore Wind":
        column = "offshore_waccs"

    sorted_df = df.sort_values(by=column, axis=0, ascending=True)
    list = ["solar_pv_wacc", "onshore_wacc", "offshore_wacc"]
    for columns in list:
        if columns == column:
            list.remove(columns)
    sorted_df = sorted_df.drop(labels=list, axis="columns")
    sorted_df = sorted_df.dropna(subset=column)
    sorted_df = sorted_df.rename(columns={column:"WACC"})
    sorted_df["WACC"] = sorted_df["WACC"].round(decimals=2)

    return sorted_df

def sort_waccs(df):

    sorted_df = df.sort_values(by="WACC", axis=0, ascending=True)
    list = ["WACC", "Equity_Cost", "Debt_Cost", "Debt_Share", "Tax_Rate"]
    sorted_df = sorted_df.drop(labels=list, axis="columns")
    
    return sorted_df


@st.cache_data
def get_selected_country(df, country_code):

    selected_wacc = df[df['Country code'] == country_code]

    return selected_wacc


def plot_ranking_table(raw_df, country_codes):

    # Select countries
    df = raw_df[raw_df["Country code"].isin(country_codes)]

    
    # Melt dataframe
    df = df.rename(columns={"Risk_Free":" Risk Free", "Country_Risk":"Country Risk", "Technology_Risk":"Technology Risk"})
    data_melted = df.melt(id_vars="Country code", var_name="Factor", value_name="Value")

    # Set order
    category_order = [' Risk Free', 'Country Risk', 'Equity Risk', 'Lenders Margin', 'Technology Risk']

    # Create chart
    chart = alt.Chart(data_melted).mark_bar().encode(
        x=alt.X('sum(Value):Q', stack='zero', title='Weighted Average Cost of Capital (%)'),
        y=alt.Y('Country code:O', sort="x", title='Country'),  # Sort countries by total value descending
        color=alt.Color('Factor:N', title='Factor'),
        order=alt.Order('Factor:O', sort="ascending"),  # Color bars by category
).properties(width=700)

    # Add x-axis to the top
    x_axis_top = chart.encode(
        x=alt.X('sum(Value):Q', stack='zero', title='Weighted Average Cost of Capital (%)', axis=alt.Axis(orient='top'))
    )

    # Combine the original chart and the one with the top axis
    chart_with_double_x_axis = alt.layer(
        chart,
        x_axis_top
    )

    st.write(chart_with_double_x_axis)

def plot_comparison_chart(df):
   # Melt dataframe
    df = df.rename(columns={"Risk_Free":" Risk Free", "Country_Risk":"Country Risk", "Technology_Risk":"Technology Risk"})
    data_melted = df.melt(id_vars="Year", var_name="Factor", value_name="Value")

    # Set order
    category_order = [' Risk Free', 'Country Risk', 'Equity Risk', 'Lenders Margin', 'Technology Risk']

    # Create chart
    chart = alt.Chart(data_melted).mark_bar().encode(
        x=alt.X('sum(Value):Q', stack='zero', title='Weighted Average Cost of Capital (%)'),
        y=alt.Y('Year:O', title='Country'),  # Sort countries by total value descending
        color=alt.Color('Factor:N', title='Factor'),
        order=alt.Order('Factor:O', sort="ascending"),  # Color bars by category
).properties(width=700)
    st.write(chart)
    


country_waccs = pd.read_csv("./DATA/Country_Waccs_2024.csv")



st.title("Financing Costs for Renewables Estimator (FINCORE)")
year = st.selectbox(
        "Year", ("2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"), 
         index=8, key="Year", placeholder="Select Year...")
technology = st.selectbox(
        "Displayed Technology", ("Solar PV", "Onshore Wind", "Offshore Wind"), 
         index=0, placeholder="Select Technology...", key="Technology")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🌐 Map", "🥇Global Estimates", "🔭Country Projections", "📈 Calculator", "ℹ️ Methods", "📝 About"])


# Calculate yearly results for solar, onshore and offshore
yearly_waccs_solar = wacc_predictor.calculate_historical_waccs(year, "Solar PV")
yearly_waccs_onshore = wacc_predictor.calculate_historical_waccs(year, "Onshore Wind")
yearly_waccs_offshore = wacc_predictor.calculate_historical_waccs(year, "Offshore Wind")


# Select specified technology for plotting
if technology == "Solar PV":
    yearly_waccs = yearly_waccs_solar
elif technology == "Onshore Wind":
    yearly_waccs = yearly_waccs_onshore
elif technology == "Offshore Wind":
    yearly_waccs = yearly_waccs_offshore



with tab1:
    st.header("Map")
    display_map(yearly_waccs, technology)
with tab2:
    st.header("Global Estimates")
    selected_countries = st.multiselect("Countries to compare", options=yearly_waccs['Country code'].values, default=["USA", "IND", "GBR", "JPN", "CHN", "BRA"])
    sorted_waccs = sort_waccs(yearly_waccs)
    plot_ranking_table(sorted_waccs, selected_countries)
with tab3:
    st.header("Country Projections")
    st.write("WORK IN PROGRESS")
    projection_year = st.slider("Year of projection", min_value=2024, max_value=2050, value=2030, step=1)
    st.line_chart(pd.DataFrame({"X": [20, 30, 40], "Y":[40, 50, 60]}))
with tab4:
    st.header("Country Calculator")
    country_code = st.selectbox(
        "Country", sorted_waccs['Country code'].sort_values(ascending=True).values, 
         index=0, placeholder="Select Country...", key="Country")
    projection_year = st.selectbox(
        "Year", np.arange(2024, 2050, 1), 
         index=6, placeholder="Select Year...", key="Projection Year")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.subheader("Macro Environment")
        rf_rate = st.number_input("Risk-free Rate (%)", value=2.5, min_value=1.0, max_value=10.0, step=0.1)
        crp = st.number_input("Country Risk Premium (%)", value=5.0, min_value=0.0, max_value=20.0, step=0.1)
    with col2:
        st.subheader("Renewable Development")
        market_maturity = st.selectbox(
        "Market Maturity",["Mature", "Intermediate", "Immature"], 
         index=2, placeholder="Select Maturity...", key="Maturity")
        tech_penetration = st.number_input("Renewable Penetration (%)", value=None, min_value=0.0, max_value=30.0, step=1.0)
    with col3:
        st.subheader("Debt-Equity Premiums")
        st.write("")
        st.write("")
        erp = st.number_input("Equity Risk Premium (%)", value=5.0, min_value=0.0, max_value=10.0, step=0.1)
        lm = st.number_input("Lenders Margin (%)", value=2.0, min_value=0.0, max_value=5.0, step=0.1)
    with col4:
        st.subheader("Financing Structure")
        st.write("")
        st.write("")
        debt_share = st.number_input("Debt Share (%)", value=60, min_value=0, max_value=100, step=10)
        tax_rate = st.number_input("Tax Rate (%)", value=25, min_value=0, max_value=50, step=1)
    st.subheader("Comparison of Projected WACC with Historical Estimates")

    # Evaluate projected data
    projected_data = wacc_predictor.calculate_country_wacc(rf_rate, crp, tax_rate, technology, market_maturity, country_code, debt_share, erp, lm, tech_penetration, projection_year)
    projected_data["Year"] = projection_year

    # Extract historical data for the given country
    selected_wacc = get_selected_country(yearly_waccs, country_code)
    selected_wacc["Year"] = year

    # Create a bar chart with historical, cost of equity, cost of debt, and overall wacc
    evaluated_wacc_data = pd.concat([selected_wacc, projected_data])
    evaluated_wacc_data = evaluated_wacc_data.drop(columns = ["Debt_Share", "Equity_Cost", "Debt_Cost", "Tax_Rate", "Country code", "WACC"])
    plot_comparison_chart(evaluated_wacc_data)

with tab5:
    text = open('about.md').read()
    st.write(text)

with tab6:
    st.subheader("About")
    st.write("FINCORE allows you to estimate the cost of capital for solar and wind located in the vast majority of the globe, both historical and future." 
            + " It aims to address the limited accessibility of empirical data on renewable financing terms, and the geographic skew towards Western and industrialising countries of the little data that is available.")
    st.subheader("Contact")
    st.write("FINCORE tool is part of Climate Compatible Growth's suite of open-source Energy Modelling Tools, and has been developed by Luke Hatton at Imperial College London. Contact by email: l.hatton23@imperial.ac.uk")
    st.subheader("License and Data Use Permissions")
    st.write("The data available from this tool is licensed as Creative Commons Attribution-NonCommercial International (CC BY-NC 4.0), which means you are free to copy, redistribute"
            + " and adapt it for non-commercial purposes, provided you give appropriate credit. If you wish to use the data for commercial purposes, please get in touch.")

    

