# Data Dictionary

This document describes the data elements from the three primary datasets used in the **Explainable AI-Driven Hospital Resource Intelligence and Optimization Platform**.

---

## 1. NHS England Beds Publication (Monthly Aggregated Timeseries)
* **Source:** NHS England UEC Daily Sitrep (`Beds-publication-Timeseries-March-2020-July-2026.xlsx`)
* **Time Span:** March 2020 - July 2026
* **Frequency:** Monthly Average
* **Scope:** National Acute Trusts (All Acutes / Type 1 acute trusts)

| Column Name | Meaning | Data Type | Source Dataset | Unit | Possible Use | Missing % | Can be Target? | Can be Feature? |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **Month** | Calendar month of observation | Object (String) | NHS Beds Excel | Month Year | Index / Time axis | 0% | No | Yes (Index) |
| **G&A beds available** | Average available General & Acute beds | Float | NHS Beds Excel | Bed Count | Capacity baseline | 0% | No | Yes |
| **G&A core beds available** | Core (planned) available General & Acute beds | Float | NHS Beds Excel | Bed Count | Base capacity indicator | 0% | No | Yes |
| **G&A escalation beds available** | Temporary escalation beds added for surge | Float | NHS Beds Excel | Bed Count | Surge indicator | 0% | No | Yes |
| **G&A covid void beds** | Beds kept empty due to COVID-19 safety spacing | Float | NHS Beds Excel | Bed Count | Infection control impact | 0% | No | Yes |
| **G&A beds occupied** | Average occupied General & Acute beds | Float | NHS Beds Excel | Bed Count | Demand trend / Historical target | 0% | **Yes** (Monthly) | Yes |
| **G&A occupancy rate** | Occupancy percentage for General & Acute beds | Float | NHS Beds Excel | Ratio (0.0 to 1.0) | Efficiency metric | 0% | **Yes** (Monthly) | Yes |
| **Adult G&A beds available** | Available Adult-specific General & Acute beds | Float | NHS Beds Excel | Bed Count | Age-specific capacity | 0% | No | Yes |
| **Adult G&A beds occupied** | Average occupied Adult General & Acute beds | Float | NHS Beds Excel | Bed Count | Age-specific demand | 0% | **Yes** (Monthly) | Yes |
| **Adult critical care beds available** | Available ICU / High Dependency beds for adults | Float | NHS Beds Excel | Bed Count | ICU Capacity baseline | 0% | No | Yes |
| **Adult critical care beds occupied** | Average occupied ICU / High Dependency beds for adults | Float | NHS Beds Excel | Bed Count | Critical care demand / Target | 0% | **Yes** (Monthly) | Yes |
| **Adult critical care occupancy rate** | Occupancy percentage for Adult ICU beds | Float | NHS Beds Excel | Ratio (0.0 to 1.0) | ICU pressure indicator | 0% | **Yes** (Monthly) | Yes |
| **7 or more days** | Number of patients with a Length of Stay (LOS) $\ge$ 7 days | Float | NHS Beds Excel | Patient Count | Long-stay indicator | 28% | No | Yes |
| **14 or more days** | Number of patients with a Length of Stay (LOS) $\ge$ 14 days | Float | NHS Beds Excel | Patient Count | Long-stay indicator | 28% | No | Yes |
| **21 or more days** | Number of patients with a Length of Stay (LOS) $\ge$ 21 days | Float | NHS Beds Excel | Patient Count | Long-stay indicator | 28% | No | Yes |

*Note: Missing percentages are relative to the "All Acutes" sheet length (76 rows). paediatric and neonatal beds columns are excluded from this table for brevity but follow a similar structure.*

---

## 2. ICU Daily Demand
* **Source:** Derived from MIMIC-IV Clinical Demo `icustays.csv.gz`
* **Time Span:** April 2110 - December 2201 (De-identified timestamps)
* **Frequency:** Daily
* **Scope:** 100-patient sample

| Column Name | Meaning | Data Type | Source Dataset | Unit | Possible Use | Missing % | Can be Target? | Can be Feature? |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **date** | Calendar date of observation | Object (Date) | Derived from `icustays` | YYYY-MM-DD | Time axis | 0% | No | Yes (Index) |
| **occupied_beds** | Active ICU stays on the given date | Integer | Derived from `icustays` | Bed Count | Target for ICU forecasting | 0% | **Yes** (Daily) | Yes |

---

## 3. ED Daily Demand
* **Source:** Derived from MIMIC-IV-ED Demo `edstays.csv.gz`
* **Time Span:** September 2112 - October 2201 (De-identified timestamps)
* **Frequency:** Daily
* **Scope:** 64-patient sample

| Column Name | Meaning | Data Type | Source Dataset | Unit | Possible Use | Missing % | Can be Target? | Can be Feature? |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **date** | Calendar date of arrival | Object (Date) | Derived from `edstays` | YYYY-MM-DD | Time axis | 0% | No | Yes (Index) |
| **arrivals** | Patient arrivals in ED on the given date | Integer | Derived from `edstays` | Patient Count | Target for ED forecasting | 0% | **Yes** (Daily) | Yes |
