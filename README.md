# Eurostat Income Analytics Pipeline

> 🚧 **Work in Progress** 🚧
> This project is currently under active development. The ETL pipeline and SQL analytical layer have been completed. The next phase is the development of an interactive Power BI dashboard.

## Overview

This project builds an end-to-end analytics workflow using publicly available Eurostat income distribution data.

The goal is to demonstrate practical data engineering and analytics skills, including:

* Data extraction directly from Eurostat
* Data cleaning and transformation using Python and Pandas
* Star schema dimensional modeling
* PostgreSQL data warehousing
* SQL-based data validation and exploratory data analysis (EDA)
* Power BI dashboard development (in progress)

## Dataset

**Source:** Eurostat

Dataset: `ilc_di03` - Income distribution by age and sex

The pipeline retrieves raw data directly from Eurostat and transforms it into an analytical warehouse structure suitable for reporting and business intelligence workloads.

## Current Project Status

### Completed

* [x] Data extraction directly from Eurostat
* [x] Data transformation and cleaning
* [x] Dimension table generation
* [x] Fact table construction
* [x] Star schema implementation
* [x] PostgreSQL loading process
* [x] Analytical SQL view creation
* [x] Data validation queries
* [x] Exploratory SQL analysis queries

### In Progress

* [ ] Power BI dashboard design
* [ ] KPI definition
* [ ] Dashboard visualizations
* [ ] Project documentation improvements

## Warehouse Schema

Current warehouse design:

```text
fact_income
│
├── dim_age
├── dim_country
├── dim_sex
├── dim_statinfo
└── dim_unit
```

## Repository Structure

```text
.
├── etl/
│   ├── dimensions.py
│   ├── extract.py
│   ├── load.py
│   ├── pipeline.py
│   ├── transform.py
│   └── utils.py
│
├── sql/
│   ├── create_views.sql
│   ├── validation.sql
│   └── eda.sql
│
├── data/
│   ├── processed
│   └── raw
│
└── README.md
```

## Upcoming Work

The next stage of the project focuses on building a Power BI dashboard to explore:

* Income trends over time
* Cross-country comparisons
* Gender income differences
* Age-group income patterns
* Mean vs. median income analysis

## Technologies

* Python
* Pandas
* PostgreSQL
* SQLAlchemy
* pgAdmin
* Power BI
* Git / GitHub

---

More updates will be added as the dashboard and analytical reporting layer are completed.