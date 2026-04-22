# ESG Supply Chain Risk Dashboard

A Streamlit web application that helps companies understand and visualize Environmental, Social, and Governance (ESG) risks hidden in their supply chains.

## What is ESG?

ESG stands for **Environmental, Social, and Governance**. It's a framework used to evaluate how a company impacts the world beyond just profit:

- **Environmental**: How does the company affect the planet? (CO2 emissions, water usage, pollution)
- **Social**: How does the company affect people? (forced labor, child labor, worker safety)
- **Governance**: How is the company managed? (corruption, transparency, ethics)

Companies that ignore ESG risks face real consequences: regulatory penalties, investor backlash, and consumer boycotts. For example, a US apparel company lost over $13 billion in revenue after being exposed for forced labor in its supply chain.

## What does this app do?

Most companies know their direct suppliers (Tier 1), but have no visibility into what happens deeper in the supply chain. A smartphone company in Japan might source copper from Chile, which is mined using equipment manufactured in China, powered by coal from Indonesia. Each step carries ESG risks.

This dashboard lets users:

1. **Upload** a simple CSV file with their supply chain cost breakdown (material, country, cost)
2. **Analyze** each sourcing country against 5 ESG risk indicators
3. **Visualize** the results through interactive charts:
   - **Radar chart**: Shows the overall risk profile across all 5 indicators at a glance
   - **Bar chart**: Breaks down which material contributes the most risk for any selected indicator
   - **World map**: Highlights which countries in the supply chain carry the highest risk
   - **Data table**: Full detailed scores, downloadable as CSV

## How does the scoring work?

Each country is scored on 5 ESG indicators using publicly available data:

| Indicator | What it measures | Source |
|-----------|-----------------|--------|
| CO2 Emissions | Carbon dioxide emissions per person | Our World in Data (Global Carbon Project) |
| Corruption | How corrupt the public sector is | Transparency International CPI 2025 |
| Forced Labor | Prevalence of modern slavery per 1,000 people | Walk Free Global Slavery Index 2023 |
| Water Stress | Ratio of water demand to available supply | WRI Aqueduct 4.0 |
| Child Labor | Percentage of children (5-17) in child labor | UNICEF (Jun 2025) |

Since each indicator uses different units (tonnes, percentages, scores), we normalize all values to a **0-10 scale** using min-max normalization:

```
score = (value - min) / (max - min) × 10
```

- **0** = lowest risk (best performing country in the dataset)
- **10** = highest risk (worst performing country in the dataset)

This allows all indicators to be compared on the same radar chart regardless of their original units.

Risk scores are then **cost-weighted**: materials with higher costs contribute more to the overall risk profile. If 60% of your spending goes to a high-risk country, that matters more than 5% spent in another high-risk country.

## Example

The app includes a sample dataset simulating an electronics manufacturer's supply chain:

| Material | Country | Cost (USD) |
|----------|---------|------------|
| Semiconductors | Taiwan | 1,200,000 |
| Lithium batteries | China | 900,000 |
| Rare earth minerals | DR Congo | 600,000 |
| Circuit boards | Vietnam | 400,000 |
| Display panels | South Korea | 350,000 |
| Plastic casing | India | 300,000 |
| Copper wiring | Chile | 250,000 |
| Assembly labor | Malaysia | 500,000 |
| Packaging | Indonesia | 150,000 |
| Shipping | Singapore | 200,000 |

This example reveals that rare earth minerals from DR Congo carry high forced labor risk, while lithium batteries from China contribute significant CO2 and corruption risk.

## Project Structure

```
esg-dashboard/
├── app.py                    # Streamlit dashboard application
├── clean_and_merge.py        # Data processing script (produces the ESG database)
├── esg_risk_by_country.csv   # Processed ESG risk database (214 countries, 5 indicators)
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Tech Stack

- **Python** — Core language
- **Streamlit** — Web application framework
- **Plotly** — Interactive charts (radar, bar, choropleth map)
- **Pandas** — Data processing and analysis
- **NumPy** — Numerical operations

## How to run locally

```bash
# Clone the repository
git clone https://github.com/MM-BOUH/esg-dashboard.git
cd esg-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Data Pipeline

If you want to rebuild the ESG database from raw source data:

1. Download the 5 raw datasets (see sources in the table above)
2. Place them in the project folder with these names:
   - `co2.csv` (Our World in Data)
   - `cpi.csv` (Transparency International, converted from xlsx)
   - `slavery.xlsx` (Walk Free)
   - `water.csv` (WRI Aqueduct via World Bank Data360)
   - `child_labor.xlsx` (UNICEF)
3. Run: `python3 clean_and_merge.py`
4. This produces a fresh `esg_risk_by_country.csv`

## Live Demo

[https://esg-mmbouh.streamlit.app](https://esg-mmbouh.streamlit.app/)

## Author

**Mohamed Mehfoud Bouh**
- LinkedIn: [linkedin.com/in/mmbouh](https://linkedin.com/in/mmbouh)
- Google Scholar: [scholar.google.com/citations?user=R5D0BCIAAAAJ](https://scholar.google.com/citations?user=R5D0BCIAAAAJ)

## License

This project is open source. The ESG data used comes from publicly available sources under their respective licenses (Creative Commons, Open Data).
