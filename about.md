The cost of capital is an essential input to technoeconomic and energy systems assessments, which reflects the cost of finance from debt and equity investors for a given energy project, but empirical data is typically limited, geographically concentrated and/or unreflective of recent macroeconomic changes (e.g., long-term interest rates). The FinCoRE tool has been developed by Climate Compatible Growth to address these empirical data gaps by providing estimates of the cost of capital, in addition to short-term forecasts. 

The tool is based on the approach developed by IRENA in their benchmarking tool, which estimates the cost of debt and cost of equity by disaggregating contributions from relevant financial and risk factors:

 * __Risk-free rate__, $r_{rf}$: Reflects the time value of money, taken as the U.S. 10 year Treasury Bond yield.
 * __Country Risk__, $r_{crp}$: The risk associated with investing in a given country, based on sovereign risk assessments performed by credit rating agencies. Country risk estimates are taken from the work of Professor Damodaran at NYU, who evaluates them from sovereign bond credit rating or spreads between the national sovereign bond and US treasury bonds.
 * __Equity Risk Premium__, $r_{erp}$: The additional risk premium for equity investors, who are paid last in the event of project default or failure. The equity risk premium is also taken here from estimates made by Professor Damodaran.
 * __Lenders Margin__, $r_{lm}$: The  profit margin taken by providers of debt, which was assumed here to be 2% based on data reported for large-scale infrastructure projects.
 * __Technology Risk__, $r_{tech}$: Risks associated with the selected energy technology being deployed, which are influenced by the maturity of the technology as well as relevant policy and regulatory support (including subsidies and market based mechanisms). It is estimated here based on the ratio of installed technology capacity to overall grid capacity.

 The cost of debt and cost of equity are calculated using the following equations:

 * __Cost of Debt__, $C_{debt}$ = $r_{rf}$ + $r_{crp}$ + $r_{lm}$ + $r_{tech}$
 * __Cost of Equity__, $C_{equity}$ = $r_{rf}$ + $r_{crp}$ + $r_{erp}$ + $r_{tech}$

 The overall cost of capital was then calculated by making assumptions over the debt share ($D_{debt}$), which increases as the risk of the project falls. Here, the debt share was assumed to range between 40-80% inversely with country risk premiums based on reported values from the Diacore and AURES II projects. Interest repayments are tax deductible in the majority of countries, so the "tax shield" effect on the cost of debt was modelled using data from the Tax Foundation on corporate tax rates ($R_{tax}$)

 * __Overall cost of capital__, $C_{overall}$ = $D_{debt}$ x $C_{debt}$ x (1-$R_{tax}$) + (1-$D_{debt}$) x $C_{equity}$