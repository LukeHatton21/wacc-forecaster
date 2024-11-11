import xarray as xr
import pandas as pd
import numpy as np

class WaccPredictor:
    def __init(self, country_categories, crp_data, generation_data, GDP, tax_data):
        """ Initialises the WACC Predictor Class, which is used to generate an estimate of the cost of capital at
         a national level for countries with available data
        
        Inputs:
        Data_path - path direction to Data inputs
        Generation_Data - Ember Yearly Generation Data for 2000-2023
        CRP_Data - Data on Country Risk Premiums, taken from Damodaran for multiple years.
        Country_codes - Country coding to ISO 3 codes
        GDP - GDP per capita data
        Collated_IR - Collated interest rate data from the IMF and OECD
        Tax_Data - Corporate Tax Rates for individual countries
        RF_rate - Risk free rates on a yearly basis
        
        """
    
        # Read in relevant inputs
        self.crp_data = pd.read_csv(crp_data)
        self.generation_data = pd.read_csv(generation_data)
        self.gdp_data = pd.read_csv(GDP)
        self.tax_data = pd.read_csv(tax_data)
        self.rf_rate = 2.6 # Add in historical calculation
       
        # Set up initial calculator
        self.historical_waccs = self.calculate_historical_waccs()


    def calculate_historical_waccs(self):

        # Set up the storage dataframe for cost of equity and cost of debt
        storage_df = pd.DataFrame(columns=["Country", "Country code", "Risk_Free_Rate", "CRP", 
                                           "Renewable_Penetration", "Equity_Cost", 
                                           "Debt_Cost", "Debt_Share", "Tax_Rate", "WACC"])
        
        # Add rows for countries with data 
        storage_df[['Country', 'Country code']] = self.crp_data[['Country', 'Country code']]

        # Create a multiindex of years and countries
        years = self.crp_data.columns.values.to_list[2:-1]
        storage_df = pd.concat([storage_df.assign(year=year) for year in years], ignore_index=True)

        # Loop over each year
        for year in years:

            # Calculate Risk Free Rate
            storage_df.loc[storage_df['year'] == year, "Risk_Free_Rate"] = self.rf_rate
            rf_rate = storage_df.loc[storage_df['year'] == year]['Risk_Free_Rate']

            # Calculate Country Risk
            storage_df.loc[storage_df['year'] == year, "CRP"] = self.crp_data[str(year)]
            country_risk = storage_df.loc[storage_df['year'] == year]['CRP']

            # Extract Equity Risk Premium
            storage_df.loc[storage_df['year'] == year, "ERP"] 

            # Extract Lenders Margin
            lenders_margin = self.lenders_margin

            # Extract Generation Data 

            # Calculate Technology Risk

            # Calculate Cost of Equity and Cost of Debt

            # Estimate Debt Share

            # Calculate Weighted Average Cost of Capital


        