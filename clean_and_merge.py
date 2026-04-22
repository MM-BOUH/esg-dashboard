"""
ESG Risk Database Builder
=========================
This script takes 5 raw public datasets and produces a single clean CSV
(esg_risk_by_country.csv) where each row is a country and each column is
an ESG risk indicator normalized to a 0–10 scale (10 = highest risk).

The output CSV will be used by our Streamlit ESG dashboard app.

Data sources:
1. CO2 emissions per capita — Our World in Data (Global Carbon Project)
2. Corruption Perception Index — Transparency International (CPI 2025)
3. Forced labor prevalence — Walk Free (Global Slavery Index 2023)
4. Water stress — WRI Aqueduct 4.0 (2030 BAU projections)
5. Child labor rate — UNICEF (Jun 2025 update)
"""

import pandas as pd
import numpy as np


def normalize_0_to_10(series):
    """
    Normalize a pandas Series to a 0–10 scale.
    
    Why: Each indicator uses different units (tonnes, percentages, scores).
    To compare them on the same radar chart, we need a common scale.
    
    Formula: (value - min) / (max - min) * 10
    - 0 means lowest risk in the dataset
    - 10 means highest risk in the dataset
    """
    min_val = series.min()
    max_val = series.max()
    
    # Avoid division by zero if all values are the same
    if max_val == min_val:
        return pd.Series(5.0, index=series.index)
    
    return ((series - min_val) / (max_val - min_val) * 10).round(2)


# ============================================================
# 1. CO2 EMISSIONS PER CAPITA
# ============================================================
# Source: Our World in Data (Global Carbon Project)
# Columns: Entity (country name), Code (ISO3), Year, CO2 per capita (tonnes)
# We only need the most recent year per country.

print("Processing CO2 emissions...")

co2_raw = pd.read_csv("co2.csv")

# Filter to the most recent year available in the dataset
latest_year = co2_raw["Year"].max()
print(f"  Latest year in dataset: {latest_year}")

co2 = co2_raw[co2_raw["Year"] == latest_year].copy()

# Drop rows that aren't real countries (e.g., "World", "Asia", "Europe")
# Real countries have a 3-letter ISO code; aggregates have NaN in the Code column
co2 = co2.dropna(subset=["Code"])

# Keep only the columns we need and rename for clarity
co2 = co2[["Code", "Entity", "CO₂ emissions per capita"]].rename(columns={
    "Code": "country_code",
    "Entity": "country_name",
    "CO₂ emissions per capita": "co2_per_capita"
})

print(f"  Countries with CO2 data: {len(co2)}")


# ============================================================
# 2. CORRUPTION PERCEPTION INDEX (CPI 2025)
# ============================================================
# Source: Transparency International
# The original .xlsx was corrupted for openpyxl, so we converted it to CSV
# using LibreOffice. The CSV has: Country, ISO3, Region, CPI 2025 score, Rank, ...
#
# IMPORTANT: CPI scores go from 0 (most corrupt) to 100 (cleanest).
# For our risk scale, we need to INVERT it: risk = 100 - CPI score.
# That way, a corrupt country (low CPI) gets a high risk score.

print("Processing Corruption data...")

# Skip 3 rows: title, embargo notice, empty line. Row 4 has the actual column headers.
cpi_raw = pd.read_csv("cpi.csv", skiprows=3)

# Keep only country code and score
cpi = cpi_raw[["ISO3", "CPI 2025 score"]].rename(columns={
    "ISO3": "country_code",
    "CPI 2025 score": "cpi_score"
})

# Drop rows with missing data
cpi = cpi.dropna(subset=["country_code", "cpi_score"])

# Convert score to numeric (might be string after CSV conversion)
cpi["cpi_score"] = pd.to_numeric(cpi["cpi_score"], errors="coerce")

# Invert: high CPI = clean = low risk, so risk = 100 - score
cpi["corruption_risk_raw"] = 100 - cpi["cpi_score"]

# Drop the original score column, we only need the inverted risk
cpi = cpi[["country_code", "corruption_risk_raw"]]

print(f"  Countries with corruption data: {len(cpi)}")


# ============================================================
# 3. FORCED LABOR / MODERN SLAVERY
# ============================================================
# Source: Walk Free, Global Slavery Index 2023
# Sheet: "GSI 2023 summary data"
# Structure: Row 0 is empty, Row 1 is section headers, Row 2 is column names,
#            Row 3 onward is data.
# Key column: "Estimated prevalence of modern slavery per 1,000 population"
# This means: how many people per 1,000 in that country are in modern slavery.
# Higher = more risk.

print("Processing Forced Labor data...")

slavery_raw = pd.read_excel("slavery.xlsx", sheet_name="GSI 2023 summary data", header=None)

# Data starts at row 3. Column 0 = country name, Column 3 = prevalence per 1,000
slavery = slavery_raw.iloc[3:].copy()
slavery = slavery[[0, 3]].rename(columns={
    0: "country_name",
    3: "forced_labor_per_1000"
})

# Convert to numeric and drop any non-numeric rows (like region summaries)
slavery["forced_labor_per_1000"] = pd.to_numeric(slavery["forced_labor_per_1000"], errors="coerce")
slavery = slavery.dropna(subset=["forced_labor_per_1000"])

# Clean country names (strip whitespace)
slavery["country_name"] = slavery["country_name"].str.strip()

print(f"  Countries with forced labor data: {len(slavery)}")


# ============================================================
# 4. WATER STRESS
# ============================================================
# Source: WRI Aqueduct 4.0 Country Rankings (via World Bank Data360)
# This dataset contains FUTURE projections (2030, 2050, 2080), not baseline.
# We use 2030 Business-as-Usual with Total gross withdrawal weight
# as the closest proxy to current conditions.
#
# The score ranges from 0 (no stress) to 5 (extremely high stress).
# Higher = more risk.

print("Processing Water Stress data...")

water_raw = pd.read_csv("water.csv")

# Filter to:
# - Year 2030 (closest to present)
# - Business as Usual scenario (most realistic)
# - Total gross withdrawal weight (overall, not sector-specific)
water = water_raw[
    (water_raw["TIME_PERIOD"] == 2030) &
    (water_raw["COMP_BREAKDOWN_1_LABEL"] == "Weight: Total gross withdrawal") &
    (water_raw["COMP_BREAKDOWN_2_LABEL"] == "Scenario: Business as Usual")
].copy()

# Keep one row per country (drop duplicates from sub-scenarios)
water = water.drop_duplicates(subset="REF_AREA", keep="first")

# Keep only the columns we need
water = water[["REF_AREA", "REF_AREA_LABEL", "OBS_VALUE"]].rename(columns={
    "REF_AREA": "country_code",
    "REF_AREA_LABEL": "country_name",
    "OBS_VALUE": "water_stress_raw"
})

print(f"  Countries with water stress data: {len(water)}")


# ============================================================
# 5. CHILD LABOR
# ============================================================
# Source: UNICEF Global Databases (Jun 2025 update)
# Sheet: "Child labour"
# Structure: Lots of header rows. Data starts at row 12.
# Column 0 = country name, Column 1 = total % of children (5-17) in child labor
# Dashes "-" mean no data available.

print("Processing Child Labor data...")

child_raw = pd.read_excel("child_labor.xlsx", sheet_name="Child labour", header=None)

# Data starts at row 12. Column 0 = country, Column 1 = percentage
child = child_raw.iloc[12:].copy()
child = child[[0, 1]].rename(columns={
    0: "country_name",
    1: "child_labor_pct"
})

# Replace dashes with NaN, then convert to numeric
child["child_labor_pct"] = child["child_labor_pct"].replace("-", np.nan)
child["child_labor_pct"] = pd.to_numeric(child["child_labor_pct"], errors="coerce")

# Drop rows without data and rows that are region summaries (usually have NaN)
child = child.dropna(subset=["child_labor_pct", "country_name"])

# Clean country names
child["country_name"] = child["country_name"].str.strip()

# Remove region/summary rows that UNICEF includes (they have ** or other markers)
child = child[~child["country_name"].str.contains(r"\*|†|‡|Summary|World|Region|Total|East and|West and|South |Middle |Sub-|Least|Latin|UNICEF", 
                                                    case=False, na=False)]

print(f"  Countries with child labor data: {len(child)}")


# ============================================================
# MERGE ALL DATASETS
# ============================================================
# Challenge: Some datasets use ISO3 country codes (CO2, CPI, Water),
# while others use country names (Slavery, Child Labor).
# We need to merge them all on a common key.
#
# Strategy:
# 1. Start with CO2 as the base (it has both country_code and country_name)
# 2. Merge CPI and Water on country_code (ISO3)
# 3. Merge Slavery and Child Labor on country_name (fuzzy matching needed)

print("\nMerging datasets...")

# Start with CO2 as base — it has the most countries and both code + name
merged = co2[["country_code", "country_name", "co2_per_capita"]].copy()

# Merge CPI on country code
merged = merged.merge(cpi, on="country_code", how="outer")

# Merge Water on country code
merged = merged.merge(
    water[["country_code", "water_stress_raw"]], 
    on="country_code", 
    how="outer"
)

# For name-based datasets, we need to handle country name variations.
# E.g., "United States" vs "United States of America"
# We'll create a name mapping for common mismatches.
name_fixes = {
    "United States of America": "United States",
    "Türkiye": "Turkey",
    "Timor-Leste": "Timor-Leste",
    "Côte d'Ivoire": "Cote d'Ivoire",
    "Cote d'Ivoire": "Cote d'Ivoire",
    "Cabo Verde": "Cape Verde",
    "Eswatini": "Eswatini",
    "Czechia": "Czech Republic",
    "Czech Republic": "Czechia",
    "Democratic Republic of the Congo": "Democratic Republic of Congo",
    "Republic of the Congo": "Congo",
    "Congo": "Congo",
    "North Macedonia": "North Macedonia",
    "Lao PDR": "Laos",
    "Laos": "Laos",
    "Viet Nam": "Vietnam",
    "Vietnam": "Vietnam",
    "South Korea": "South Korea",
    "Hong Kong": "Hong Kong",
    "Taiwan": "Taiwan",
    "North Korea": "North Korea",
    "Myanmar": "Myanmar",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
}

# Apply name fixes to slavery and child labor datasets
def fix_name(name):
    """Standardize country names for merging."""
    if pd.isna(name):
        return name
    name = name.strip()
    return name_fixes.get(name, name)

slavery["country_name"] = slavery["country_name"].apply(fix_name)
child["country_name"] = child["country_name"].apply(fix_name)

# Fill in missing country_name in merged from the water dataset
# (some countries might be in water but not in CO2)
water_names = water.set_index("country_code")["country_name"]
for idx, row in merged.iterrows():
    if pd.isna(row["country_name"]) and row["country_code"] in water_names.index:
        merged.at[idx, "country_name"] = water_names[row["country_code"]]

# Now merge slavery and child labor on country_name
merged["country_name_clean"] = merged["country_name"].apply(fix_name)

slavery_for_merge = slavery.rename(columns={"country_name": "country_name_clean"})
child_for_merge = child.rename(columns={"country_name": "country_name_clean"})

merged = merged.merge(slavery_for_merge, on="country_name_clean", how="left")
merged = merged.merge(child_for_merge, on="country_name_clean", how="left")

# Drop the temporary clean name column
merged = merged.drop(columns=["country_name_clean"])

print(f"  Total countries after merge: {len(merged)}")


# ============================================================
# NORMALIZE ALL INDICATORS TO 0–10 SCALE
# ============================================================
# Each indicator has different units and ranges.
# We normalize them all to 0–10 so they're comparable on a radar chart.
# 10 always means HIGHEST RISK.

print("Normalizing to 0-10 scale...")

merged["co2_risk"] = normalize_0_to_10(merged["co2_per_capita"])
merged["corruption_risk"] = normalize_0_to_10(merged["corruption_risk_raw"])
merged["forced_labor_risk"] = normalize_0_to_10(merged["forced_labor_per_1000"])
merged["water_stress_risk"] = normalize_0_to_10(merged["water_stress_raw"])
merged["child_labor_risk"] = normalize_0_to_10(merged["child_labor_pct"])


# ============================================================
# FINAL CLEANUP
# ============================================================
# Keep only the columns we need for the dashboard.
# Drop countries that have no data for any indicator.

final = merged[[
    "country_code", 
    "country_name",
    "co2_risk",
    "corruption_risk",
    "forced_labor_risk",
    "water_stress_risk",
    "child_labor_risk"
]].copy()

# Drop rows where ALL risk scores are NaN (country has no useful data)
risk_cols = ["co2_risk", "corruption_risk", "forced_labor_risk", 
             "water_stress_risk", "child_labor_risk"]
final = final.dropna(subset=risk_cols, how="all")

# Sort by country name for readability
final = final.sort_values("country_name").reset_index(drop=True)

# Calculate an overall risk score (average of available indicators per country)
# This is useful for the choropleth map
final["overall_risk"] = final[risk_cols].mean(axis=1).round(2)

# Save the final dataset
final.to_csv("esg_risk_by_country.csv", index=False)

print(f"\nFinal dataset saved: esg_risk_by_country.csv")
print(f"  Total countries: {len(final)}")
print(f"  Countries with all 5 indicators: {final[risk_cols].dropna().shape[0]}")
print(f"  Columns: {list(final.columns)}")

# Show a sample
print("\nSample data:")
print(final[final["country_name"].isin(["Japan", "China", "United States", "India", "Germany", "Australia"])].to_string(index=False))
