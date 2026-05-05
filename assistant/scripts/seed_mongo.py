"""
Seed MongoDB from esg_risk_by_country.csv.

Run from the repo root:
    python -m assistant.scripts.seed_mongo

Creates two collections:
  countries  - one doc per country with all 5 risk scores + overall_risk
  suppliers  - demo supplier records with risk scores inherited from their country

Idempotent: drops and recreates both collections on each run.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pandas as pd

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from assistant.db.mongo import countries_col, suppliers_col

RISK_COLS = [
    "co2_risk",
    "corruption_risk",
    "forced_labor_risk",
    "water_stress_risk",
    "child_labor_risk",
]

SOURCES = {
    "co2_risk": {
        "name": "Our World in Data / Global Carbon Project",
        "url": "https://ourworldindata.org/co2-emissions",
        "indicator": "CO2 Emissions",
    },
    "corruption_risk": {
        "name": "Transparency International CPI 2025",
        "url": "https://www.transparency.org/en/cpi",
        "indicator": "Corruption Perception Index",
    },
    "forced_labor_risk": {
        "name": "Walk Free Global Slavery Index 2023",
        "url": "https://www.walkfree.org/global-slavery-index/",
        "indicator": "Forced Labor",
    },
    "water_stress_risk": {
        "name": "WRI Aqueduct 4.0",
        "url": "https://www.wri.org/aqueduct",
        "indicator": "Water Stress",
    },
    "child_labor_risk": {
        "name": "UNICEF Jun 2025",
        "url": "https://data.unicef.org/topic/child-protection/child-labour/",
        "indicator": "Child Labor",
    },
}

DEMO_SUPPLIERS = [
    {"name": "TaiwanSemi Co.", "material": "Semiconductors", "country_name": "Taiwan", "cost_usd": 1_200_000},
    {"name": "ShenBat Energy", "material": "Lithium batteries", "country_name": "China", "cost_usd": 900_000},
    {"name": "KivuMin SARL", "material": "Rare earth minerals", "country_name": "Democratic Republic of Congo", "cost_usd": 600_000},
    {"name": "VietCircuit Ltd.", "material": "Circuit boards", "country_name": "Vietnam", "cost_usd": 400_000},
    {"name": "SeoDisplay Inc.", "material": "Display panels", "country_name": "South Korea", "cost_usd": 350_000},
    {"name": "MumbaiMold Pvt.", "material": "Plastic casing", "country_name": "India", "cost_usd": 300_000},
    {"name": "CopperAndes S.A.", "material": "Copper wiring", "country_name": "Chile", "cost_usd": 250_000},
    {"name": "KL Assemble Sdn.", "material": "Assembly labor", "country_name": "Malaysia", "cost_usd": 500_000},
    {"name": "JavaPack PT", "material": "Packaging", "country_name": "Indonesia", "cost_usd": 150_000},
    {"name": "SingaLog Pte.", "material": "Shipping", "country_name": "Singapore", "cost_usd": 200_000},
    {"name": "DhakaTex Ltd.", "material": "Textiles", "country_name": "Bangladesh", "cost_usd": 320_000},
    {"name": "BrasilSteel S.A.", "material": "Steel components", "country_name": "Brazil", "cost_usd": 410_000},
    {"name": "MexiPlast S.A. de C.V.", "material": "Injection molding", "country_name": "Mexico", "cost_usd": 270_000},
    {"name": "PhilAssembly Corp.", "material": "Final assembly", "country_name": "Philippines", "cost_usd": 380_000},
    {"name": "ThaiRubber Co.", "material": "Rubber seals", "country_name": "Thailand", "cost_usd": 190_000},
]


def load_csv() -> pd.DataFrame:
    csv_path = Path(__file__).resolve().parents[2] / "esg_risk_by_country.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    return pd.read_csv(csv_path)


def seed_countries(df: pd.DataFrame) -> dict[str, dict]:
    """Insert country docs. Returns a name->doc lookup for the supplier seed step."""
    col = countries_col()
    col.drop()

    docs = []
    name_index: dict[str, dict] = {}

    for _, row in df.iterrows():
        doc = {
            "country_code": row["country_code"],
            "country_name": row["country_name"],
            "overall_risk": round(float(row["overall_risk"]), 2) if pd.notna(row["overall_risk"]) else None,
            "indicators": {},
            "sources": {},
        }

        for col_name in RISK_COLS:
            val = row.get(col_name)
            doc["indicators"][col_name] = round(float(val), 2) if pd.notna(val) else None
            doc["sources"][col_name] = SOURCES[col_name]

        docs.append(doc)
        name_index[row["country_name"]] = doc

    col.insert_many(docs)
    print(f"  countries: inserted {len(docs)} docs")
    return name_index


def seed_suppliers(name_index: dict[str, dict]) -> None:
    col = suppliers_col()
    col.drop()

    docs = []
    random.seed(42)

    for i, tmpl in enumerate(DEMO_SUPPLIERS):
        country_doc = name_index.get(tmpl["country_name"])
        if country_doc is None:
            print(f"  WARNING: country not found: {tmpl['country_name']}, skipping supplier {tmpl['name']}")
            continue

        doc = {
            "supplier_id": f"S{i + 1:03d}",
            "name": tmpl["name"],
            "material": tmpl["material"],
            "country_code": country_doc["country_code"],
            "country_name": tmpl["country_name"],
            "cost_usd": tmpl["cost_usd"],
            "overall_risk": country_doc["overall_risk"],
            "indicators": country_doc["indicators"],
        }
        docs.append(doc)

    col.insert_many(docs)
    print(f"  suppliers: inserted {len(docs)} docs")


def main() -> None:
    print("Seeding MongoDB...")
    df = load_csv()
    name_index = seed_countries(df)
    seed_suppliers(name_index)
    print("Done.")


if __name__ == "__main__":
    main()
