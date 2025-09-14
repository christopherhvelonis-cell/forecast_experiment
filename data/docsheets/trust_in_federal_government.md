# Data Sheet: Trust in Federal Government

**Indicator ID:** trust_in_federal_government  
**Definition:** Share of Americans saying they trust the federal government “just about always” or “most of the time.”  
**Unit:** Percent (%)  
**Source:** Pew Research Center – *Public Trust in Government: 1958–2024*  
**Coverage Years:** 1958–2022 (annual, survey-based)  
**Frequency:** Annual  
**Vintage Availability:** Limited; Pew harmonizes multiple polls. Archival vintages available only through Roper iPoll/ANES microdata.  
**Revision Policy:** No regular revisions (survey data is stable once published).  
**Mode Changes:**  
- 1958–1970: Gallup-originated surveys  
- 1972–2000: Mix of ANES + other national polls  
- 2000–2022: Pew + Gallup series harmonized  

**Transform Spec:** logit_share (since it’s a bounded percentage).  

**Break Flags:**  
- 1972 (Nixon/Watergate inflection)  
- 1994 (midterm + Clinton realignment)  
- 2008–2010 (financial crisis)  
- 2016 (sharp partisan divide)  

**Known Issues:**  
- Harmonization blends multiple pollsters; cross-year comparability can be affected.  
- Archival vintages not fully accessible in Pew’s public CSV → treat as **scenario-only** for strict scored evaluation.  

**Usage:**  
- Scorable for long-run cultural legitimacy trends.  
- Event catalog link: `trust_below_20` (used for Brier scoring).  
