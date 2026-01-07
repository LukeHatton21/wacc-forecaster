import streamlit as st
import folium
import pandas as pd
import numpy as np
from streamlit_folium import st_folium
import branca.colormap as cm
import altair as alt
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class VisualiserClass:
    def __init__(self, crp_data, tech_premium):
        """ Initialises the VisualiserClass, which is used to generate plots for the webtool """

        # Read in Data
        self.crp_data = crp_data
        self.tech_premium = tech_premium


        # Get country name and country code dictionary
        self.crp_country = self.crp_data[["Country", "Country code"]]
        self.crp_country = self.crp_country.loc[self.crp_country["Country code"] != "ERP"]
        self.crp_dictionary = pd.Series(self.crp_country["Country code"].values,index=self.crp_country["Country"]).to_dict()
        self.crp_dict_reverse = self.inverse_dict(self.crp_dictionary)

        # Get tech name and coding dictionary
        self.techs = self.tech_premium[["NAME", "TECH"]]
        self.techs = self.techs.loc[self.techs["TECH"] != "OTHER"]
        self.tech_dictionary = pd.Series(self.techs["TECH"].values,index=self.techs["NAME"]).to_dict()
        self.tech_dict_reverse = self.inverse_dict(self.tech_dictionary)

    def inverse_dict(self, dictionary):
        inv_dict = {v: k for k, v in dictionary.items()}
        return inv_dict
    
    def display_map(self, df, technology):
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
    def get_sorted_waccs(self, df, technology):

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

    def sort_waccs(self, df):

        sorted_df = df.sort_values(by="WACC", axis=0, ascending=True)
        list = ["WACC", "Equity_Cost", "Debt_Cost", "Debt_Share", "Tax_Rate"]
        sorted_df = sorted_df.drop(labels=list, axis="columns")
        
        return sorted_df


    @st.cache_data
    def get_selected_country(self,df, country_code):

        selected_wacc = df[df['Country code'] == country_code]

        return selected_wacc


    def plot_ranking_table(self, raw_df, country_codes):

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

    def plot_comparison_chart(self, df):
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


    def create_chloropleth_map(self, wacc_coverage):

        fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=['IEA Cost of Capital Observatory', 'Calcaterra et al. 2025',"Steffen 2020", 'This Work'],
        specs=[[{'type': 'choropleth'}, {'type': 'choropleth'}],
               [{'type': 'choropleth'}, {'type': 'choropleth'}]],
        vertical_spacing=0.03,
        horizontal_spacing=0.03
    )

        color_scales = {
            'FINCORE': 'Blues',
            'IEA': 'Reds',
            'STEFFEN': 'greys',
            'IRENA':'Greens',
        }

        for i, col in enumerate(['IEA', 'IRENA','STEFFEN','FINCORE']):
            fig.add_trace(
                go.Choropleth(
                    locations=wacc_coverage['Country code'],
                    z=wacc_coverage[col],
                    colorscale=color_scales[col],
                    zmin=wacc_coverage[col].min(),
                    zmax=wacc_coverage[col].max(),
                    colorbar_title=col,
                    locationmode='ISO-3',
                    showscale=False,
                ),
                row=(i//2) + 1, col=(i%2) + 1
            )
            fig.update_geos(
            row=(i//2) + 1, col=(i%2) + 1,
            projection_type='robinson',
            lataxis=dict(range=[-60, 85]),  # Set latitude bounds
            lonaxis=dict(range=[-180, 180])
            )
            fig.write_image(f"GlobalCoverage" + str(col) + ".png") # Set longitude bounds (full range))
        fig.update_layout(
        margin=dict(t=30, b=10, l=10, r=10),
        height=600,
        width=600
        )
        for annotation in fig['layout']['annotations']:
            annotation['y'] -= 0.01  # Adjusted for vertical stacking)

        

        fig.show()

        fig.write_image("GlobalCoverage.png", scale=5)

    def produce_boxplots_verification(self, historical_data, technology, iea_data): 
    
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
        fig.savefig("Verification_" + technology + ".png", dpi=2400)
        plt.show() 

    def produce_boxplots_by_year(self, data, technology): 
    
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
        fig.savefig("Future_" + technology + ".png", dpi=2400)
        plt.show() 