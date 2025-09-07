import xarray as xr
import pandas as pd
import numpy as np
import streamlit as st

class WaccCalculator:
    def __init__(self, tech_premiums, penetration_boundaries, maturity_premiums):
        """ Initialises the WACC Calculator Class, which is used to calculate an estimate of the cost of capital at
         a national level for countries with available data for a specific technology
        
        Inputs:
        tech_premiums: CSV containing mapping of relative tech premiums, measured compared to solar
        
        """
    
        # Read in relevant inputs
        self.tech_premiums = pd.read_csv(tech_premiums)
        self.penetration_boundaries = pd.read_csv(penetration_boundaries)
        self.maturity_premiums = pd.read_csv(maturity_premiums)

        # Set up initial assumptions
        self.lenders_margin = 2
        

    def calculate_country_wacc(self, rf_rate, crp, cds, tax_rate, technology, year, debt_share=None, erp=None, tech_penetration=None, market_maturity=None, country_code=None):
        

        # Calculate maturity of market and tech premium
        tech_maturity = self.calculate_maturity_tech_premium(technology, tech_penetration)
        technology_premium = tech_maturity.loc[tech_maturity["Country code"] != "ERP", "Tech_Premium"]

        # Calculate relative technology premium
        relative_premium = self.lookup_tech_premium(technology)
        if technology in ["Wind", "Wind Offshore", "Solar"]:
            technology_premium = technology_premium
        else:
            technology_premium = technology_premium + relative_premium

        # Extract country code
        if country_code is None:
            country_code = crp.loc[crp["Country code"] != "ERP", "Country code"]
        
        # Extract values
        if 'Country code' in crp.columns:
            crp = crp.loc[crp["Country code"] != "ERP", "CRP_"+str(year)]
            cds = cds.loc[cds["Country code"] != "ERP", "CDS_"+str(year)]
            tax_rate = tax_rate.loc[tax_rate["Country code"] != "ERP", "Tax_Rate"]
        

        
        # Calculate debt share, if applicable
        if debt_share is None:
            debt_share = self.calculate_debt_share(crp)


        # Calculate the cost of equity
        debt_cost = rf_rate + cds + self.lenders_margin + technology_premium

        # Calculate the cost of debt
        equity_cost = rf_rate + crp + erp + technology_premium

        # Calculate the weighted average cost of capital
        estimated_wacc = debt_cost * (debt_share/100) * (1 - (tax_rate/100)) + equity_cost * (1 - (debt_share/100))

        # Extract contributions to the overall WACC
        risk_free_contributions = rf_rate*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))
        crp_contributions = cds*(debt_share / 100 * (1 - tax_rate/100)) + crp*(1 - debt_share / 100)
        erp_contributions = erp * ( 1 - (debt_share / 100))
        lm_contributions = self.lenders_margin * (debt_share / 100) * (1-tax_rate/100)
        tech_premium_contributions = technology_premium*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))


        # Include in a pandas dataframe
        results_df = pd.DataFrame(data={"Country code": country_code, "Risk_Free":risk_free_contributions, "Country_Risk": crp_contributions, "Equity Risk": erp_contributions, "Lenders Margin": lm_contributions, 
                                        "Technology_Risk": tech_premium_contributions, "Equity_Cost": equity_cost, "Debt_Cost": debt_cost, "WACC": estimated_wacc, "Debt_Share": debt_share, "Tax_Rate": tax_rate, "Year":year})
        

        return results_df
    

    def calculate_maturity_tech_premium(self, technology, tech_penetration):

        # Extract boundaries for the given technology
        tech_boundaries = self.penetration_boundaries
        maturity_premiums = self.maturity_premiums
        
        # Check if technology has specific boundaries
        if tech_boundaries["TECH"].isin([technology]).any():
            tech_boundaries_selected = tech_boundaries.loc[tech_boundaries["TECH"]==technology]
            maturity_premium_selected = maturity_premiums.loc[maturity_premiums["TECH"]==technology]
        else:
            tech_boundaries_selected = tech_boundaries.loc[tech_boundaries["TECH"]=="Other"]
            maturity_premium_selected = maturity_premiums.loc[maturity_premiums["TECH"]=="Other"]

        # Establish the boundaries
        intermediate = tech_boundaries_selected["INTERMEDIATE"].values[0]
        mature = tech_boundaries_selected["MATURE"].values[0]

        # Establish the premiums
        maturity_premium = maturity_premium_selected["MATURE"].values[0]
        intermediate_premium = maturity_premium_selected["INTERMEDIATE"].values[0]
        immature_premium = maturity_premium_selected["IMMATURE"].values[0]
        

        # Calculate the maturity based on boundaries
        tech_penetration["Maturity"] = tech_penetration.apply(
            lambda row: "Mature" if row["Penetration"] > mature 
            else ("Intermediate"if row["Penetration"] > intermediate
                else "Immature"),
            axis=1
            ) 
        
        # Calculate the intermediate premium
        tech_penetration["Intermediate"]= (maturity_premium - immature_premium)/(mature - intermediate)*(tech_penetration["Penetration"]-intermediate) + immature_premium
        
        tech_penetration["Tech_Premium"] = tech_penetration.apply(
            lambda row: maturity_premium if row["Maturity"] == "Mature"
            else (row["Intermediate"] if row["Maturity"] == "Intermediate"
                else immature_premium),
            axis=1
            )
        tech_penetration = tech_penetration.drop(columns=["Intermediate"])

        return tech_penetration
    
    def calculate_debt_share(self, crp, max_crp=None):

        # Calculate debt share based on CRP, assuming it ranges in line with CRP data
        debt_share = 80 - 40 * (crp / np.nanmax(crp))

        return debt_share
    

    def calculate_debt_share_individual(self, crp):

        # Calculate debt share based on CRP, assuming it ranges in line with CRP data
        debt_share = 80 - 40 * (crp / 25)

        return debt_share

    def lookup_tech_premium(self, technology):

        # Extract relative tech premium
        tech_premiums = self.tech_premiums

        # Locate the value of the tech premium
        if tech_premiums["TECH"].isin([technology]).any():
            relative_premium = tech_premiums.loc[tech_premiums["TECH"]==technology]["PREMIUM"].values[0]
        else:
            relative_premium = tech_premiums.loc[tech_premiums["TECH"]=="Other"]["PREMIUM"].values[0]
        
        return relative_premium



    def calculate_wacc_individual(self, rf_rate, crp, cds, tax_rate, technology, year, country_code, tech_penetration, debt_share=None, erp=None, market_maturity=None, penetration_value=None):
        

        # Calculate maturity of market and tech premium
        if penetration_value is not None:
            tech_penetration = pd.DataFrame({"Country code": [country_code], "Penetration":penetration_value})
        tech_maturity = self.calculate_maturity_tech_premium(technology, tech_penetration)
        technology_premium = tech_maturity.loc[tech_maturity["Country code"] != "ERP", "Tech_Premium"]
            
        # Calculate relative technology premium
        relative_premium = self.lookup_tech_premium(technology)
        if technology in ["Wind", "Wind Offshore", "Solar"]:
            technology_premium = technology_premium
        else:
            technology_premium = technology_premium + relative_premium
        
        # Calculate debt share, if applicable
        if debt_share is None:
            debt_share = self.calculate_debt_share_individual(crp)

        # Calculate the cost of equity
        debt_cost = rf_rate + cds + self.lenders_margin + technology_premium

        # Calculate the cost of debt
        equity_cost = rf_rate + crp + erp + technology_premium

        # Calculate the weighted average cost of capital
        estimated_wacc = debt_cost * (debt_share/100) * (1 - (tax_rate/100)) + equity_cost * (1 - (debt_share/100))

        # Extract contributions to the overall WACC
        risk_free_contributions = rf_rate*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))
        crp_contributions = cds*(debt_share / 100 * (1 - tax_rate/100)) + crp*(1 - debt_share / 100)
        erp_contributions = erp * ( 1 - (debt_share / 100))
        lm_contributions = self.lenders_margin * (debt_share / 100) * (1-tax_rate/100)
        tech_premium_contributions = technology_premium*((debt_share / 100 * (1 - tax_rate/100)) + (1 - debt_share / 100))


        # Include in a pandas dataframe
        results_df = pd.DataFrame(data={"Country code": country_code, "Risk_Free":risk_free_contributions, "Country_Risk": crp_contributions, "Equity Risk": erp_contributions, "Lenders Margin": lm_contributions, 
                                        "Technology_Risk": tech_premium_contributions, "Equity_Cost": equity_cost, "Debt_Cost": debt_cost, "WACC": estimated_wacc, "Debt_Share": debt_share, "Tax_Rate": tax_rate, "Year":year})
        

        return results_df
    







    def tech_premium_individual(self, technology, tech_penetration, market_maturity=None):

        # Extract boundaries for the given technology
        tech_boundaries = self.penetration_boundaries
        maturity_premiums = self.maturity_premiums
        
        # Check if technology has specific boundaries
        if tech_boundaries["TECH"].isin([technology]).any():
            tech_boundaries_selected = tech_boundaries.loc[tech_boundaries["TECH"]==technology]
            maturity_premium_selected = maturity_premiums.loc[maturity_premiums["TECH"]==technology]
        else:
            tech_boundaries_selected = tech_boundaries.loc[tech_boundaries["TECH"]=="Other"]
            maturity_premium_selected = maturity_premiums.loc[maturity_premiums["TECH"]=="Other"]

        # Establish the boundaries
        intermediate = tech_boundaries_selected["INTERMEDIATE"].values[0]
        mature = tech_boundaries_selected["MATURE"].values[0]

        # Establish the premiums
        maturity_premium = maturity_premium_selected["MATURE"].values[0]
        intermediate_premium = maturity_premium_selected["INTERMEDIATE"].values[0]
        immature_premium = maturity_premium_selected["IMMATURE"].values[0]
        

        # Calculate the maturity based on boundaries
        if tech_penetration > mature:
            maturity = "Mature"
        elif tech_penetration > intermediate:
            maturity = "Intermediate"
        else:
            maturity = "Immature"

        # If maturity is specified, take that
        if market_maturity is not None:
            maturity = market_maturity

        # Calculate tech premiunm
        if maturity == "Mature":
            tech_premium = maturity_premium
        elif maturity == "Intermediate":
            tech_premium = (maturity_premium - immature_premium)/(mature - intermediate)*(tech_penetration-intermediate) + immature_premium
        else:
            tech_premium = immature_premium


        return tech_premium