import xarray as xr
import pandas as pd
import numpy as np
import streamlit as st

class WaccPredictor:
    def __init__(self, crp_data, generation_data, GDP, tax_data, ember_targets, us_ir):
        """ Initialises the WACC Predictor Class, which is used to generate an estimate of the cost of capital at
         a national level for countries with available data
        
        Inputs:
        Data_path - path direction to Data inputs
        Generation_Data - Ember Yearly Generation Data for 2000-2023
        CRP_Data - Data on Country Risk Premiums, taken from Damodaran for multiple years.
        Country_codes - Country coding to ISO 3 codes
        GDP - GDP per capita data
        Tax_Data - Corporate Tax Rates for individual countries
        RF_rate - Risk free rates on a yearly basis
        Ember_targets - Targets for 2030 selected from Ember
        US_IR - Projections of the U.S. long term interest rates conducted by the CBO alongside OECD IR data

        
        """
    
        # Read in relevant inputs
        self.crp_data = pd.read_csv(crp_data)
        self.generation_data = pd.read_csv(generation_data)
        self.gdp_data = pd.read_csv(GDP)
        self.tax_data = pd.read_csv(tax_data)

        # Read in projections of data
        self.renewable_projections = pd.read_csv(ember_targets)
        self.ir_data = pd.read_csv(us_ir)
       
        # Set up initial assumptions
        self.lenders_margin = 2
        

    def calculate_historical_waccs(self, year, technology):

        def fill_missing_RE_values(data, previous_year, year):

            # Set Country Code as index
            data.set_index('Country code', inplace=True)
            previous_year.set_index('Country code', inplace=True)

            # Fill missing values for 2023 with 2022 data
            data = pd.merge(data, previous_year, on="Country code", how="outer")
            data['Penetration_' + str(year)] = data['Penetration_' + str(year)].fillna(data['Penetration_'+str(year-1)])

            # Reset index if needed
            data.reset_index(inplace=True)

            return data
        
        # Convert year into a string
        year_str = str(year)
        year_int = int(year)

        # Extract long term U.S. interest rates (proxy for risk free rate)
        rf_rate = self.ir_data[self.ir_data['Country code'] == "USA"][year_str].values[0].astype(float)

        # Extract CRPs
        crps = self.pull_CRP_data(year_str)
        erp = crps[crps['Country code']=="ERP"]["CRP_"+year_str][0]
        crp_data = crps["CRP_"+year_str]

        # Extract Generation Data
        if technology == "Solar PV":
            ember_name = "Solar"
        elif technology == "Onshore Wind":
            ember_name = "Wind"
        elif technology == "Offshore Wind":
            ember_name = "Wind"
        generation_data = self.pull_generation_data_v2(year_str, ember_name)
        previous_year = self.pull_generation_data_v2(str(year_int-1), ember_name)
        generation_data = fill_missing_RE_values(generation_data, previous_year, year_int)
        generation_data = pd.merge(self.crp_data['Country code'],generation_data[['Country code', 'Penetration_'+year_str]], on="Country code", how="left")

        # Extract Tax Rates
        tax_rate = pd.merge(self.crp_data['Country code'], self.tax_data[['Country code', 'Tax_Rate']], on="Country code", how="left")
        tax_rate['Tax_Rate'] = tax_rate['Tax_Rate'].fillna(value=0)
        tax_data = tax_rate['Tax_Rate'].values.astype(float)
                           

        # Calculate WACC and contributions
        results = self.calculate_irena_wacc(rf_rate=rf_rate, crp=crp_data, tax_rate=tax_data, technology=technology, erp=erp, lm=self.lenders_margin,
                                            tech_penetration=generation_data['Penetration_'+year_str], country_codes=self.crp_data['Country code'])

        return results

    def pull_CRP_data(self, year):

        
        # Extract generation data
        data = self.crp_data
        
        # Extract specific year
        data_subset = data[["Country", "Country code", year]]
        data_subset = data_subset.rename(columns={year: "CRP_"+year})
        
        
        return data_subset
    

    def pull_generation_data_v2(self, year_str, technology):

        
        # Extract generation data
        generation_data = self.generation_data
        year = int(year_str)
        
        # Extract Capacity
        capacity_subset = generation_data[(generation_data['Year'] == year) & (generation_data['Category'] == "Capacity") & (generation_data['Unit'] == "GW")]                                             
        capacity_data = capacity_subset[capacity_subset['Variable'] == technology]
        capacity_data = capacity_data.rename(columns = {"Value" : "Capacity_" + year_str, "YoY absolute change": "Capacity_" + year_str + "_YoY_Change"})

        
        # Extract Penetration
        penetration_subset = generation_data[(generation_data['Year'] == year) & (generation_data['Category'] ==  "Electricity generation") & (generation_data['Unit'] == "%")]  
        penetration_data = penetration_subset[penetration_subset['Variable'] == technology]
        penetration_data = penetration_data.rename(columns = {"Value" : "Penetration_" + year_str, "YoY absolute change": "Penetration_" + year_str + "_YoY_Change"})

        
        # Extract needed data
        penetration_data = penetration_data[["Area", "Country code", "Year", "Continent", "Penetration_" + year_str,"Penetration_" + year_str + "_YoY_Change"]]
        capacity_data  = capacity_data[["Country code", "Capacity_" + year_str, "Capacity_" + year_str + "_YoY_Change"]]
        data_for_output = pd.merge(penetration_data, capacity_data, on="Country code", how="outer")

        # Extract only data that is present in the CRP dataset
        data_for_output = pd.merge(self.crp_data['Country code'], data_for_output, how="left", on="Country code")
        
        return data_for_output


    def calculate_country_wacc(self, rf_rate, crp, tax_rate, technology, market_maturity, country_code, debt_share=None, erp=None, lm=None, tech_penetration=None, year=None):
        

        
        # Calculate maturity of market
        if tech_penetration is not None:
            if technology == "Onshore Wind" or "Solar PV":
                if tech_penetration > 10:
                    maturity = "Mature"
                elif tech_penetration > 5:
                    maturity = "Intermediate"
                else: 
                    maturity = "Immature"
            else:
                if tech_penetration > 6:
                    maturity = "Mature"
                elif tech_penetration > 3:
                    maturity = "Intermediate"
                else: 
                    maturity = "Immature"
        else:
            maturity = market_maturity
            


        # Calculate technology premium
        if maturity == "Mature":
            technology_premium = 1.5
        elif maturity == "Intermediate":
            technology_premium = 2.375
        else:
            technology_premium = 3.25
        
        # Calculate debt share, if applicable
        if debt_share is None:
            if maturity == "Mature":
                debt_share = 80
            elif maturity == "Intermediate":
                debt_share = 70
            elif maturity == "Immature":
                debt_share = 60

        # Calculate the cost of equity
        debt_cost = rf_rate + crp + lm + technology_premium

        # Calculate the cost of debt
        equity_cost = rf_rate + crp + erp + technology_premium

        # Calculate the weighted average cost of capital
        estimated_wacc = debt_cost * (debt_share/100) * (1 - (tax_rate/100)) + equity_cost * (1 - (debt_share/100))

        # Extract contributions to the overall WACC
        risk_free_contributions = rf_rate*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))
        crp_contributions = crp*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))
        erp_contributions = erp * ( 1 - (debt_share / 100))
        lm_contributions = lm * (debt_share / 100) * (1-tax_rate/100)
        tech_premium_contributions = technology_premium*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))
        

        # Include in a pandas dataframe
        results_df = pd.DataFrame(data={"Country code": country_code, "Risk_Free":risk_free_contributions, "Country_Risk": crp_contributions, "Equity Risk": erp_contributions, "Lenders Margin": lm_contributions, 
                                        "Technology_Risk": tech_premium_contributions, "Equity_Cost": equity_cost, "Debt_Cost": debt_cost, "WACC": estimated_wacc, "Debt_Share": debt_share, "Tax_Rate": tax_rate}, index=[str(year)])
        
        return results_df
    

    def calculate_irena_wacc(self, rf_rate, crp, tax_rate, technology, erp, lm, tech_penetration, country_codes):


        # Calculate technology premium
        def calculate_technology_premium(maturity):
            premium = np.empty_like(maturity, dtype=float)
            premium[maturity == "Mature"] = 1.5
            premium[maturity == "Intermediate"] = 2.375
            premium[maturity == "Immature"] = 3.25
            return premium

        # Calculate debt share
        def calculate_debt_share(maturity):
            debt_share = np.empty_like(maturity, dtype=float)
            debt_share[maturity == "Mature"] = 80
            debt_share[maturity == "Intermediate"] = 70
            debt_share[maturity == "Immature"] = 60
            return debt_share
     
        # Fill locations where tech penetration is empty with 
        tech_penetration = np.where(np.isnan(tech_penetration), 0, tech_penetration)
        tech_penetration = np.where(tech_penetration == None, 0, tech_penetration)


        # Calculate maturity of market
        maturity = np.empty_like(tech_penetration, dtype=object)
        if technology in ["Onshore Wind", "Solar PV"]:
            maturity[tech_penetration > 10] = "Mature"
            maturity[(tech_penetration > 5) & (tech_penetration <= 10)] = "Intermediate"
            maturity[tech_penetration <= 5] = "Immature"
        else:
            maturity[tech_penetration > 6] = "Mature"
            maturity[(tech_penetration > 3) & (tech_penetration <= 6)] = "Intermediate"
            maturity[tech_penetration <= 3] = "Immature"

        # Calculate technology premium
        technology_premium = calculate_technology_premium(maturity)

        # Calculate debt share
        debt_share = calculate_debt_share(maturity)

        # Calculate the cost of equity
        debt_cost = rf_rate + crp + lm + technology_premium

        # Calculate the cost of debt
        equity_cost = rf_rate + crp + erp + technology_premium

        # Calculate the weighted average cost of capital
        estimated_wacc = debt_cost * (debt_share/100) * (1 - (tax_rate/100)) + equity_cost * (1 - (debt_share/100))
        
        # For offshore wind, add a 1% premium
        if technology == "Offshore Wind":
            estimated_wacc = estimated_wacc + 1

        # Extract contributions to the overall WACC
        risk_free_contributions = rf_rate*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))
        crp_contributions = crp*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))
        erp_contributions = erp * ( 1 - (debt_share / 100))
        lm_contributions = lm * (debt_share / 100) * (1-tax_rate/100)
        tech_premium_contributions = technology_premium*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))

        # Build Dataframe for results
        results_df = pd.DataFrame(data={"Country code": country_codes, "Risk_Free":risk_free_contributions.round(decimals=2), "Country_Risk": crp_contributions.round(decimals=2), "Equity Risk": erp_contributions.round(decimals=2), "Lenders Margin": lm_contributions, 
                                        "Technology_Risk": tech_premium_contributions.round(decimals=2), "Equity_Cost": equity_cost.round(decimals=2), "Debt_Cost": debt_cost.round(decimals=2), "WACC": estimated_wacc.round(decimals=2), "Debt_Share": debt_share, "Tax_Rate": tax_rate})
        results_df = results_df.tail(-1)

        return results_df

    
    def calculate_future_wacc(self, technology):

        # Calculate 2023 WACC for the given technology
        self.calculate_historical_waccs(2023, technology)

        # Extract 

        

        
