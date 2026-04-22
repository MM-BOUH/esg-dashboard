"""
ESG Supply Chain Risk Dashboard
================================
A Streamlit web application that lets users upload their supply chain cost data
and visualizes ESG risks across 5 indicators using public datasets.

How it works:
1. User uploads a CSV with columns: material, country, cost_usd
2. The app matches each country to our pre-built ESG risk database
3. It calculates cost-weighted risk scores (materials with higher costs
   contribute more to overall risk)
4. Results are shown as: radar chart, bar chart by material, world heatmap,
   and a downloadable data table

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np


# ============================================================
# PAGE CONFIGURATION
# ============================================================
# Must be the first Streamlit command in the script.
# "wide" layout uses the full browser width instead of a narrow centered column.
st.set_page_config(
    page_title="ESG Supply Chain Risk Dashboard",
    page_icon="🌍",
    layout="wide"
)


# ============================================================
# LOAD THE ESG RISK DATABASE
# ============================================================
# @st.cache_data tells Streamlit to load this file once and cache it.
# Without caching, it would re-read the CSV every time the user interacts
# with the app (e.g., clicks a button), which slows things down.

@st.cache_data
def load_esg_data():
    """Load the pre-built ESG risk database (produced by clean_and_merge.py)."""
    return pd.read_csv("esg_risk_by_country.csv")

esg_data = load_esg_data()

# These are the 5 ESG risk indicators we track
RISK_COLUMNS = [
    "co2_risk", "corruption_risk", "forced_labor_risk",
    "water_stress_risk", "child_labor_risk"
]

# Human-readable labels for display on charts
RISK_LABELS = [
    "CO2 Emissions", "Corruption", "Forced Labor",
    "Water Stress", "Child Labor"
]

# Mapping from label to column name (used for the dropdown selector)
LABEL_TO_COL = dict(zip(RISK_LABELS, RISK_COLUMNS))


# ============================================================
# HEADER
# ============================================================
st.title("🌍 ESG Supply Chain Risk Dashboard")
st.markdown(
    "Upload your supply chain cost data to analyze Environmental, Social, "
    "and Governance risks across your sourcing countries. "
    "Risk scores are on a **0–10 scale** (10 = highest risk)."
)


# ============================================================
# SIDEBAR: FILE UPLOAD AND INFO
# ============================================================
with st.sidebar:
    st.header("📁 Upload Data")
    st.markdown(
        "Upload a CSV file with your supply chain cost breakdown. "
        "Required columns:"
    )
    st.code("material, country, cost_usd", language=None)

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type="csv",
        help="Each row = one material/input with its sourcing country and cost"
    )

    st.divider()

    st.header("ℹ️ About")
    st.markdown(
        """
        **Data Sources:**
        - CO2: Our World in Data (Global Carbon Project)
        - Corruption: Transparency International CPI 2025
        - Forced Labor: Walk Free Global Slavery Index 2023
        - Water Stress: WRI Aqueduct 4.0
        - Child Labor: UNICEF (Jun 2025)

        **Built by:** Mohamed Mehfoud Bouh

        **Method:** Each country is scored 0–10 per indicator 
        based on normalized public data. Cost-weighted averages 
        show how your spending distribution affects overall risk.
        """
    )


# ============================================================
# SAMPLE DATA (shown when no file is uploaded)
# ============================================================
# This helps users understand the expected format before they upload.
# We use an electronics supply chain as the example because it covers
# real ESG issues: rare earth mining (forced labor), lithium (environment),
# and a diverse set of countries that light up the world map.

# ######
# It's a consumer electronics product, like a smartphone or laptop. Each row represents one component in the manufacturing supply chain:

# Semiconductors from Taiwan (TSMC is there)
# Lithium batteries from China (world's largest battery producer)
# Rare earth minerals from DRC (cobalt mining, high forced labor risk)
# Circuit boards from Vietnam (growing electronics manufacturing hub)
# Display panels from South Korea (Samsung, LG)
# Plastic casing from India (cheap manufacturing)
# Copper wiring from Chile (world's largest copper producer)
# Assembly labor from Malaysia (major electronics assembly country)
# Packaging from Indonesia
# Shipping from Singapore (major logistics hub)


sample_data = pd.DataFrame({
    "material": [
        "Semiconductors", "Lithium batteries", "Rare earth minerals",
        "Circuit boards", "Display panels", "Plastic casing",
        "Copper wiring", "Assembly labor", "Packaging", "Shipping"
    ],
    "country": [
        "Taiwan", "China", "Democratic Republic of Congo",
        "Vietnam", "South Korea", "India",
        "Chile", "Malaysia", "Indonesia", "Singapore"
    ],
    "cost_usd": [
        1200000, 900000, 600000,
        400000, 350000, 300000,
        250000, 500000, 150000, 200000
    ]
})


# ============================================================
# MAIN APPLICATION LOGIC
# ============================================================
if uploaded_file is not None:
    # ── Read the uploaded CSV ──
    supply_chain = pd.read_csv(uploaded_file)

    # Validate that required columns exist
    required_cols = {"material", "country", "cost_usd"}
    if not required_cols.issubset(supply_chain.columns):
        st.error(
            f"Missing columns. Your CSV must have: {required_cols}. "
            f"Found: {set(supply_chain.columns)}"
        )
        st.stop()

    # ── Match uploaded countries to our ESG database ──
    # We try matching on country_name first.
    # Strip whitespace to avoid mismatches like "Japan " vs "Japan"
    supply_chain["country"] = supply_chain["country"].str.strip()

    merged = supply_chain.merge(
        esg_data,
        left_on="country",
        right_on="country_name",
        how="left"
    )

    # Check for unmatched countries and warn the user
    unmatched = merged[merged["country_code"].isna()]["country"].unique()
    if len(unmatched) > 0:
        st.warning(
            f"⚠️ Could not match these countries to the ESG database: "
            f"**{', '.join(unmatched)}**. They will be excluded from the analysis. "
            f"Check spelling or try the full country name."
        )

    # Drop unmatched rows
    merged = merged.dropna(subset=["country_code"])

    if len(merged) == 0:
        st.error("No countries could be matched. Please check your CSV.")
        st.stop()

    # ── Calculate cost-weighted risk scores ──
    # Why cost-weighted? Because a material that costs $5M matters more
    # to your risk profile than one that costs $50K.
    # Weight = material cost / total cost
    total_cost = merged["cost_usd"].sum()
    merged["cost_weight"] = merged["cost_usd"] / total_cost

    # For each indicator, multiply the risk score by the cost weight
    for col in RISK_COLUMNS:
        merged[f"weighted_{col}"] = merged["cost_weight"] * merged[col]

    # ── Show summary metrics at the top ──
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Materials", len(merged))
    with col2:
        st.metric("Countries Involved", merged["country"].nunique())
    with col3:
        overall = merged["overall_risk"].mean()
        st.metric("Avg. Overall Risk", f"{overall:.1f} / 10")

    st.divider()

    # ════════════════════════════════════════════════════════
    # SECTION 1: RADAR CHART — Overall Supply Chain Risk Profile
    # ════════════════════════════════════════════════════════
    # The radar chart shows the aggregate risk across all 5 indicators.
    # Each axis = one indicator. The shape shows where risk is concentrated.

    st.header("📊 Overall Supply Chain Risk Profile")

    # Calculate aggregate (cost-weighted sum) for each indicator
    aggregate_scores = []
    for col in RISK_COLUMNS:
        # Sum of (weight * risk) across all materials = weighted average risk
        score = merged[f"weighted_{col}"].sum()
        aggregate_scores.append(round(score, 2))

    # Plotly radar charts need the data to "close" the shape,
    # so we append the first value again at the end
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=aggregate_scores + [aggregate_scores[0]],
        theta=RISK_LABELS + [RISK_LABELS[0]],
        fill="toself",
        name="Your Supply Chain",
        fillcolor="rgba(31, 119, 180, 0.3)",
        line=dict(color="rgba(31, 119, 180, 1)", width=2),
    ))

    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],  # Fixed scale so the chart is always comparable
                tickvals=[2, 4, 6, 8, 10],
            )
        ),
        showlegend=False,
        height=450,
        margin=dict(t=30, b=30),
    )

    st.plotly_chart(fig_radar, use_container_width=True)

    # Show the actual numbers below the chart
    score_df = pd.DataFrame({
        "Indicator": RISK_LABELS,
        "Weighted Risk Score": aggregate_scores
    })
    st.dataframe(score_df, use_container_width=True, hide_index=True)

    st.divider()

    # ════════════════════════════════════════════════════════
    # SECTION 2: BAR CHART — Risk Breakdown by Material
    # ════════════════════════════════════════════════════════
    # Lets the user pick an indicator and see which material
    # contributes the most risk for that specific dimension.

    st.header("📦 Risk Breakdown by Material")

    # Dropdown to select which ESG indicator to visualize
    selected_label = st.selectbox(
        "Select ESG Indicator",
        RISK_LABELS,
        help="Choose which risk dimension to analyze by material"
    )
    selected_col = LABEL_TO_COL[selected_label]

    # Create the bar chart
    fig_bar = px.bar(
        merged.sort_values(selected_col, ascending=False),
        x="material",
        y=selected_col,
        color="country",
        title=f"{selected_label} Risk by Material",
        labels={
            selected_col: "Risk Score (0-10)",
            "material": "Material",
            "country": "Country"
        },
        color_discrete_sequence=px.colors.qualitative.Set2,
    )

    fig_bar.update_layout(
        xaxis_title="Material",
        yaxis_title="Risk Score (0-10)",
        yaxis=dict(range=[0, 10]),
        height=450,
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════
    # SECTION 3: WORLD MAP — Geographic Risk Distribution
    # ════════════════════════════════════════════════════════
    # A choropleth map showing overall risk for each country
    # in the supply chain. Color intensity = risk level.

    st.header("🗺️ Geographic Risk Distribution")

    # Aggregate risk per country (in case multiple materials come from same country)
    # Use cost-weighted average per country
    country_grouped = merged.groupby(["country_code", "country"]).agg(
        total_cost=("cost_usd", "sum"),
        **{col: (col, "mean") for col in RISK_COLUMNS},
        overall_risk=("overall_risk", "mean"),
    ).reset_index()

    fig_map = px.choropleth(
        country_grouped,
        locations="country_code",
        color="overall_risk",
        hover_name="country",
        hover_data={
            "country_code": False,
            "overall_risk": ":.2f",
            "total_cost": ":,.0f",
        },
        color_continuous_scale="RdYlGn_r",  # Red=high risk, Green=low risk
        range_color=[0, 10],
        title="Overall ESG Risk by Country",
        labels={
            "overall_risk": "Overall Risk",
            "total_cost": "Total Cost (USD)",
        },
    )

    fig_map.update_layout(
        height=500,
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type="natural earth",
        ),
        margin=dict(t=50, b=0, l=0, r=0),
    )

    st.plotly_chart(fig_map, use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════
    # SECTION 4: DETAILED DATA TABLE
    # ════════════════════════════════════════════════════════
    # Shows all the raw data so users can verify and explore.
    # Also provides a download button for the analysis results.

    st.header("📋 Detailed Analysis Data")

    # Select columns to display (don't show internal weighted columns)
    display_cols = [
        "material", "country", "cost_usd", "cost_weight",
    ] + RISK_COLUMNS + ["overall_risk"]

    display_df = merged[display_cols].copy()

    # Format cost_weight as percentage for readability
    display_df["cost_weight"] = (display_df["cost_weight"] * 100).round(1)
    display_df = display_df.rename(columns={"cost_weight": "cost_weight_%"})

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Download button — lets user save the analysis results
    csv_download = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Analysis Results as CSV",
        data=csv_download,
        file_name="esg_supply_chain_analysis.csv",
        mime="text/csv",
    )

else:
    # ════════════════════════════════════════════════════════
    # NO FILE UPLOADED — Show instructions and sample data
    # ════════════════════════════════════════════════════════

    st.info("👈 Upload a CSV file in the sidebar to start your analysis.")

    st.header("📝 Expected CSV Format")
    st.markdown(
        "Your CSV should have three columns: the **material** or input name, "
        "the **country** it's sourced from, and the **cost in USD**."
    )

    st.dataframe(sample_data, use_container_width=True, hide_index=True)

    # Provide a download button for the sample data so users can test
    sample_csv = sample_data.to_csv(index=False)
    st.download_button(
        label="📥 Download Sample CSV",
        data=sample_csv,
        file_name="sample_supply_chain.csv",
        mime="text/csv",
    )

    st.divider()

    # ── Show the ESG database coverage ──
    st.header("🌐 ESG Risk Database Coverage")
    st.markdown(f"Our database covers **{len(esg_data)} countries** across 5 indicators.")

    # Show a world map of overall risk from the database
    fig_world = px.choropleth(
        esg_data.dropna(subset=["overall_risk"]),
        locations="country_code",
        color="overall_risk",
        hover_name="country_name",
        color_continuous_scale="RdYlGn_r",
        range_color=[0, 10],
        title="Global ESG Risk Overview",
        labels={"overall_risk": "Overall Risk Score"},
    )

    fig_world.update_layout(
        height=500,
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type="natural earth",
        ),
        margin=dict(t=50, b=0, l=0, r=0),
    )

    st.plotly_chart(fig_world, use_container_width=True)
