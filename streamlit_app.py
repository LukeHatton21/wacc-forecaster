import streamlit as st
import folium
import pandas as pd
import numpy as np
from streamlit_folium import st_folium
import branca.colormap as cm
from wacc_prediction_v2 import WaccPredictor
from visualiser import VisualiserClass
import altair as alt
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.lines as mlines
from matplotlib.legend_handler import HandlerTuple
# Data Source for map: https://public.opendatasoft.com/explore/embed/dataset/world-administrative-boundaries-countries/table/




def display_map(df, technology):
    map = folium.Map(location=[10, 0], zoom_start=1, control_scale=True, scrollWheelZoom=True, tiles='CartoDB positron')
    df = df.rename(columns={"Country code":"iso3_code"})
    df = df.tail(-1)

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

    # Drop year
    df = df.drop(labels="Year", axis="columns")

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

def plot_ranking_table_tech(raw_df, tech_codes):

    # Select techs
    df = raw_df[raw_df["Technology"].isin(tech_codes)]
    df["Technology"].replace(visualiser.tech_dict_reverse, inplace=True)

    # Drop year
    new_df = df.drop(columns=["Year", "Country code"])

    # Melt dataframe
    new_df = new_df.rename(columns={"Risk_Free":" Risk Free", "Country_Risk":"Country Risk", "Technology_Risk":"Technology Risk"})
    data_melted = new_df.melt(id_vars="Technology", var_name="Factor", value_name="Value")

    # Set order
    category_order = [' Risk Free', 'Country Risk', 'Equity Risk', 'Lenders Margin', 'Technology Risk']

    # Create chart
    chart = alt.Chart(data_melted).mark_bar().encode(
        x=alt.X('sum(Value):Q', stack='zero', title='Weighted Average Cost of Capital (%)'),
        y=alt.Y('Technology:O', sort="x", title='Technology'),  # Sort technologies by total value descending
        color=alt.Color('Factor:N', title='Factor').legend(orient="right", columns=3),
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
    
# Call WaccPredictor Object
wacc_predictor = WaccPredictor(crp_data = "./DATA/CRPs.csv", 
generation_data="./DATA/Ember Yearly Data 2023.csv", GDP="./DATA/GDPPerCapita.csv",
tax_data="./DATA/CORPORATE_TAX_DATA.csv", ember_targets="./DATA/Ember_2030_Targets.csv", 
us_ir="./DATA/US_IR.csv", imf_data="./DATA/IMF_Projections.csv", collated_crp_cds="./DATA/Collated_CRP_CDS.xlsx")

# Call visualiser
visualiser = VisualiserClass(wacc_predictor.crp_data, wacc_predictor.calculator.tech_premiums)
country_names = sorted(visualiser.crp_dictionary.keys())
tech_names = sorted(visualiser.tech_dictionary.keys())
tech_names = [x for x in tech_names if x !="Other"]



st.title("Financing Costs for Renewables Estimator (FinCoRE)")
year = st.selectbox(
        "Year", ("2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"), 
         index=9, key="Year", placeholder="Select Year...")
technology = st.selectbox(
        "Displayed Technology", tech_names, 
         index=7, placeholder="Select Technology...", key="Technology")
technology = visualiser.tech_dictionary.get(technology)
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["🌐 Map", "🥇Global Estimates", "🔭Country Projections", "🛠️Technologies", "📈 Calculator", "ℹ️ Methods", "📝 About"])


yearly_waccs = wacc_predictor.calculate_historical_waccs(year, technology)


with tab1:
    st.header("Map")
    display_map(yearly_waccs, technology)
with tab2:
    st.header("Global Estimates")
    selected_countries = st.multiselect("Countries to compare", options=yearly_waccs['Country code'].values, default=["USA", "IND", "GBR", "JPN", "CHN", "BRA"])
    sorted_waccs = sort_waccs(yearly_waccs)
    plot_ranking_table(sorted_waccs, selected_countries)
with tab3:
    st.header("Historical and Projected Estimates")
    country_selection = st.selectbox(
        "Country", options=country_names, 
         index=None, placeholder="Select Country of Interest...", key="CountryProjections")
    country_selection = visualiser.crp_dictionary.get(country_selection)
    options = ["Interest Rate Change", "Renewable Growth", "GDP Change"]
    options_mapping = {"Interest Rate Change": "interest_rate", "Renewable Growth": "renewable_targets", "GDP Change": "gdp_change"}
    if country_selection is not None:
        projection_assumptions = st.pills("Projection Assumptions", options, selection_mode="multi")
        for i in projection_assumptions:
            name = options_mapping.get(i)
            globals()[f"{name}"] = f"{name}"
        if "Interest Rate Change" not in projection_assumptions:
            interest_rate = None
        if "Renewable Growth" not in projection_assumptions:
            renewable_targets = None
        if "GDP Change" not in projection_assumptions:
            gdp_change = None
        historical_country_data = wacc_predictor.year_range_wacc(start_year=2015, end_year=2023, 
                                                             technology=technology, country=country_selection)
        if len(projection_assumptions) > 0:
            future_waccs = wacc_predictor.projections_wacc(end_year=2029, technology=technology, country=country_selection, 
                                                    interest_rates=interest_rate, GDP_change=gdp_change, renewable_targets=renewable_targets)
            historical_country_data = pd.concat([future_waccs, historical_country_data])
        historical_country_data = historical_country_data.drop(columns = ["Debt_Share", "Equity_Cost", "Debt_Cost", "Tax_Rate", "Country code", "WACC"])
        plot_comparison_chart(historical_country_data)

with tab4:
    st.header("Technology Comparison")
    country_tech_selection = st.selectbox(
        "Country", options=country_names, 
         index=None, placeholder="Select Country of Interest...", key="CountryTechs")
    selected_techs = st.multiselect("Technologies to compare", options=tech_names, default=["Solar PV", "Hydroelectric", "Gas Power (CCGT)"])
    print(tech_names)
    selected_techs = [visualiser.tech_dictionary.get(x) for x in selected_techs]
    country_tech_selection = visualiser.crp_dictionary.get(country_tech_selection)
    
    if country_tech_selection is not None:
        country_technology_comparison = wacc_predictor.calculate_technology_wacc(year=year, country=country_tech_selection, technologies=selected_techs)
        sorted_tech_comparison = sort_waccs(country_technology_comparison)
        plot_ranking_table_tech(sorted_tech_comparison, selected_techs)

with tab5:
    st.header("Country Calculator")
    country_code = st.selectbox(
        "Country", country_names, 
         index=0, placeholder="Select Country...", key="Country")
    country_code = visualiser.crp_dictionary.get(country_code)
    col1, col2, col3, col4 = st.columns(4)
    yearly_data = wacc_predictor.calculate_yearly_wacc(year, technology, country_code)
    with col1:
        st.subheader("Macro Environment")
        rf_rate = st.number_input("Risk-free Rate (%)", value=2.5, min_value=1.0, max_value=10.0, step=0.1)
        crp = st.number_input("Country Risk Premium (%)", value=5.0, min_value=0.0, max_value=20.0, step=0.1)
    with col2:
        st.subheader("Renewable Development")
        market_maturity = st.selectbox(
        "Market Maturity",["Mature", "Intermediate", "Immature"], 
         index=2, placeholder="Select Maturity...", key="Maturity")
        tech_penetration = st.number_input("Renewable Penetration (%)", value=0.0, min_value=0.0, max_value=30.0, step=1.0)
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
    st.subheader("Comparison of Calculated WACC with Historical Estimates")

    # Evaluate projected data
    projection_year = 2030
    projected_data = wacc_predictor.calculator.calculate_wacc_individual(rf_rate=rf_rate, crp=crp, cds=crp, tax_rate=tax_rate, technology=technology, country_code=country_code, 
                                                                         year=projection_year,erp=erp,tech_penetration=tech_penetration, market_maturity=market_maturity, penetration_value=tech_penetration)
    projected_data["Year"] = projection_year

    # Extract historical data for the given country
    selected_wacc = get_selected_country(yearly_waccs, country_code)
    selected_wacc["Year"] = year

    # Create a bar chart with historical, cost of equity, cost of debt, and overall wacc
    evaluated_wacc_data = pd.concat([selected_wacc, projected_data])
    evaluated_wacc_data = evaluated_wacc_data.drop(columns = ["Debt_Share", "Equity_Cost", "Debt_Cost", "Tax_Rate", "Country code", "WACC"])
    plot_comparison_chart(evaluated_wacc_data)


with tab6:
    text = open('about.md').read()
    st.write(text)

with tab7:
    st.subheader("About")
    st.write("FINCORE allows you to estimate the cost of capital for solar and wind located in the vast majority of the globe, both historical and future." 
            + " It aims to address the limited accessibility of empirical data on renewable financing terms, and the geographic skew towards Western and industrialising countries of the little data that is available.")
    st.subheader("Contact")
    st.write("FINCORE tool is part of Climate Compatible Growth's suite of open-source Energy Modelling Tools, and has been developed by Luke Hatton at Imperial College London. Contact by email: l.hatton23@imperial.ac.uk")
    st.subheader("License and Data Use Permissions")
    st.write("The data available from this tool is licensed as Creative Commons Attribution-NonCommercial International (CC BY-NC 4.0), which means you are free to copy, redistribute"
            + " and adapt it for non-commercial purposes, provided you give appropriate credit. If you wish to use the data for commercial purposes, please get in touch.")


def produce_aggregated_historical_data(wacc_predictor, tech_names):
    counter = 0   
    counter_year = 0 
    for year in np.arange(2015, 2025):
        for technology in tech_names:
            technology = visualiser.tech_dictionary.get(technology)
            yearly_waccs = wacc_predictor.calculate_historical_waccs(year, technology)
            wacc_data = yearly_waccs
            wacc_data["Technology"] = technology
            print(wacc_data)
            if counter == 0:
                merged_df = wacc_data[["Country code", "WACC", "Year", "Technology"]]
            else:
                merged_df = pd.concat([merged_df, wacc_data[["Country code", "WACC", "Year", "Technology"]]])
            counter = counter + 1
        if counter_year == 0:
            results_df = merged_df
        else:
            results_df = pd.concat([results_df, merged_df])
        counter_year = counter_year + 1
    print(np.unique(results_df["Year"]))
    results_df["WACC"] = results_df["WACC"].round(2)
    results_df.to_csv("./DATA/HISTORICAL_WACCS.csv")

def produce_aggregated_future_data(wacc_predictor, tech_names):
    counter = 0   
    counter_country = 0 
    for country in country_names:
        country_code = visualiser.crp_dictionary.get(country) 
        for technology in tech_names:
            technology = visualiser.tech_dictionary.get(technology)
            future_waccs = wacc_predictor.projections_wacc(end_year=2030, technology=technology, country=country_code, 
                                                    interest_rates="Yes", GDP_change="Yes", renewable_targets="Yes")
            wacc_data = future_waccs
            wacc_data["Technology"] = technology
            print(wacc_data)
            if counter == 0:
                merged_df = wacc_data[["Country code", "WACC", "Year", "Technology"]]
            else:
                merged_df = pd.concat([merged_df, wacc_data[["Country code", "WACC", "Year", "Technology"]]])
            counter = counter + 1
        if counter_country == 0:
            results_df = merged_df
        else:
            results_df = pd.concat([results_df, merged_df])
        counter_country = counter_country + 1
    results_df["WACC"] = results_df["WACC"].round(2)
    results_df.to_csv("./DATA/FUTURE_WACCS.csv")


# Produce data for output
def produce_data_for_output():
    irena = pd.read_csv("./DATA/IRENA_DATA.csv", encoding='latin1')
    iea = pd.read_csv("./DATA/IEA_CoC.csv")
    fincore = pd.read_csv("./DATA/HISTORICAL_WACCS.csv")
    steffen = pd.read_csv("./DATA/Steffen_CoC_2020.csv")
    fincore = fincore.assign(FINCORE=1)
    fincore = fincore.loc[fincore["Year"]==2023]
    fincore["FINCORE"] = 1
    wacc_coverage = fincore[["Country code", "FINCORE"]].merge(irena[["Country code", "IRENA"]], how="left").merge(iea[["Country code", "IEA"]], how="left", on="Country code").merge(steffen[["Country code", "STEFFEN"]], how="left", on="Country code")
    visualiser.create_chloropleth_map(wacc_coverage)

def fischer_equation(min, max):

    inflation = 0.03
    # Calculate for minimum and maximum
    min_nominal = (1 + min/100) * (1 + inflation) - 1
    max_nominal = (1 + max/100) * (1 + inflation) - 1

    return min_nominal*100, max_nominal*100

def produce_boxplots_by_year(data, technology): 
    
    # Extract required data
    extracted_data = data.loc[data["Technology"]==technology]

    # Melt dataframe
    df = pd.pivot_table(extracted_data[["Country code", "Year", "WACC"]], index=["Country code"], values=["WACC"], columns=["Year"])
    df.columns = df.columns.get_level_values(1)
    df.columns = df.columns.astype(str)
    # Produce boxplot
    fig, ax = plt.subplots(figsize=(10, 6))
    data_to_plot = [df[col].dropna().values for col in df.columns]
    box = ax.boxplot(data_to_plot, tick_labels=df.columns, whis=1, sym="", medianprops=dict(color="black", linewidth=2))

    # Add y labels and the shading
    ax.set_ylabel("Weighted Average Cost of Capital, " + technology + " (%)")
    min_iea, max_iea = fischer_equation(min=5, max=9)
    ax.axhspan(min_iea, max_iea, xmin=0, xmax=1, alpha=0.5, color="lightsteelblue", label="WACC range in IEA WEO scenarios")

    # Add risk free rate
    rf_rate = pd.read_csv("./DATA/US_IR.csv")[df.columns]
    ax.plot(range(1, len(df.columns) + 1), rf_rate.values[0], linestyle="--", label="Projected risk-free rate")
    ax.legend(loc="upper right")
    ax.set_ylim([0, 25])
    
    fig.tight_layout()  
    fig.savefig("Future_" + technology + ".png")
    plt.show() 

#produce_aggregated_historical_data(wacc_predictor, tech_names)
#produce_aggregated_future_data(wacc_predictor, tech_names)
#data = pd.read_csv("./DATA/HISTORICAL_WACCS.csv")
#future_data = pd.read_csv("./DATA/FUTURE_WACCS.csv")
#concat_data = pd.concat([data, future_data], ignore_index=True)
#concat_data = concat_data.round(decimals=1)
#concat_data = concat_data.merge(visualiser.crp_country, how="left", on="Country code")
#concat_data = concat_data[["Country", "Country code", "Year", "Technology", "WACC"]]
#concat_data = concat_data.loc[concat_data["Country code"] != "ABD"]
#concat_data.sort_values("Country")
#concat_data.to_csv("./DATA/WACC_ESTIMATES_LONG.csv")
#concat_wide = pd.pivot_table(concat_data, index=["Country", "Country code", "Technology"], values="WACC", columns=["Year"])
#concat_wide = concat_wide.rename(columns={"Year":"index"})
#concat_wide.to_csv("./DATA/WACC_ESTIMATES_WIDE.csv")
#produce_boxplots_by_year(future_data, "Solar")


def produce_boxplots_verification(historical_data, technology, iea_data): 
    
    # Produce mapping
    mapping = {"IND": "India", "IDN": "Indonesia", "BRA": "Brazil", "MEX": "Mexico", "ZAF": "South Africa"}
    
    # Extract required data
    extracted_data = historical_data[["Technology", "Country code", "Year", "WACC"]]
    merged_data = iea_data.merge(extracted_data.rename(columns={"WACC":"Estimated_WACC"}), how="left", on=["Technology", "Country code", "Year"])
    merged_data = merged_data[["Country code", "Year", "WACC", "Estimated_WACC"]]
    merged_data["Country code"] = merged_data["Country code"].map(mapping)
    predicted_results = merged_data[["Country code", "Year", "Estimated_WACC"]].drop_duplicates()

    # Produce boxplot
    fig, ax = plt.subplots(figsize=(10, 6))
    my_pal = {2019: "#D8BFD8", 2021: "#C680D7", 2022: "#6742B1"}
    sns.boxplot(x="Country code", y="WACC", hue="Year", data=merged_data, ax=ax, palette=my_pal)
    sns.boxplot(x="Country code", y="Estimated_WACC", hue="Year", data=predicted_results, ax=ax, color="red", legend=False, linecolor="black",capprops={"linewidth": 3, "color": "black"})
    #ax.plot([], [], color='red', label='Estimated WACCs')

    # Add y labels and the shading
    ax.set_ylabel("Weighted Average Cost of Capital, " + technology + " (%)")

    # Fix legend

    # Create three segments for the icon
    left = mlines.Line2D([0], [0], color="black", linewidth=1)   # thin left
    mid  = mlines.Line2D([0], [0], color="black", linewidth=3)   # thick middle
    right= mlines.Line2D([0], [0], color="black", linewidth=1)   # thin right

    # Bundle them into a tuple so they behave as one legend entry
    custom_icon = (left, mid, right)
    handles, labels = ax.get_legend_handles_labels()

    # Append your custom one
    handles.append(custom_icon)
    labels.append("Estimated WACC")
    ax.legend(handles, labels, loc="upper center",handler_map={tuple: HandlerTuple(ndivide=None)})
    
    fig.tight_layout()  
    fig.savefig("Verification_" + technology + ".png")
    plt.show() 

#iea_data = pd.read_csv("./DATA/IEACoCData.csv")
#produce_boxplots_verification(data, technology, iea_data)





