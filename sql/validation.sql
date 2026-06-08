-- ==========================================================
-- EUROSTAT INCOME DATA WAREHOUSE VALIDATION
-- ==========================================================
-- Purpose:
-- Verify data quality, dimensional integrity, completeness,
-- and warehouse consistency after ETL execution.
-- ==========================================================

-- ==========================================================
-- SECTION 1: TABLE ROW COUNTS
-- ==========================================================

SELECT 'fact_income' AS table_name, COUNT(*) AS row_count
FROM fact_income

UNION ALL

SELECT 'dim_country', COUNT(*)
FROM dim_country

UNION ALL

SELECT 'dim_age', COUNT(*)
FROM dim_age

UNION ALL

SELECT 'dim_sex', COUNT(*)
FROM dim_sex

UNION ALL

SELECT 'dim_unit', COUNT(*)
FROM dim_unit

UNION ALL

SELECT 'dim_statinfo', COUNT(*)
FROM dim_statinfo;

-- ==========================================================
-- SECTION 2: PRIMARY KEY VALIDATION
-- ==========================================================

SELECT country_id, COUNT(*)
FROM dim_country
GROUP BY country_id
HAVING COUNT(*) > 1;

SELECT age_id, COUNT(*)
FROM dim_age
GROUP BY age_id
HAVING COUNT(*) > 1;

SELECT sex_id, COUNT(*)
FROM dim_sex
GROUP BY sex_id
HAVING COUNT(*) > 1;

SELECT unit_id, COUNT(*)
FROM dim_unit
GROUP BY unit_id
HAVING COUNT(*) > 1;

SELECT statinfo_id, COUNT(*)
FROM dim_statinfo
GROUP BY statinfo_id
HAVING COUNT(*) > 1;

-- ==========================================================
-- SECTION 3: DIMENSION NATURAL KEY UNIQUENESS
-- ==========================================================

SELECT country_code, COUNT(*)
FROM dim_country
GROUP BY country_code
HAVING COUNT(*) > 1;

SELECT age_group, COUNT(*)
FROM dim_age
GROUP BY age_group
HAVING COUNT(*) > 1;

SELECT sex, COUNT(*)
FROM dim_sex
GROUP BY sex
HAVING COUNT(*) > 1;

SELECT unit, COUNT(*)
FROM dim_unit
GROUP BY unit
HAVING COUNT(*) > 1;

SELECT statinfo, COUNT(*)
FROM dim_statinfo
GROUP BY statinfo
HAVING COUNT(*) > 1;

-- ==========================================================
-- SECTION 4: FOREIGN KEY INTEGRITY
-- ==========================================================

SELECT COUNT(*) AS orphan_country_keys
FROM fact_income f
LEFT JOIN dim_country d USING(country_id)
WHERE d.country_id IS NULL;

SELECT COUNT(*) AS orphan_age_keys
FROM fact_income f
LEFT JOIN dim_age d USING(age_id)
WHERE d.age_id IS NULL;

SELECT COUNT(*) AS orphan_sex_keys
FROM fact_income f
LEFT JOIN dim_sex d USING(sex_id)
WHERE d.sex_id IS NULL;

SELECT COUNT(*) AS orphan_unit_keys
FROM fact_income f
LEFT JOIN dim_unit d USING(unit_id)
WHERE d.unit_id IS NULL;

SELECT COUNT(*) AS orphan_statinfo_keys
FROM fact_income f
LEFT JOIN dim_statinfo d USING(statinfo_id)
WHERE d.statinfo_id IS NULL;

-- ==========================================================
-- SECTION 5: FACT TABLE DUPLICATE CHECK
-- ==========================================================

SELECT
	country_id,
	age_id,
	sex_id,
	unit_id,
	statinfo_id,
	year,
	COUNT(*) AS occurrences
FROM fact_income
GROUP BY
	country_id,
	age_id,
	sex_id,
	unit_id,
	statinfo_id,
	year
HAVING COUNT(*) > 1;

-- ==========================================================
-- SECTION 6: NULL CHECKS
-- ==========================================================

SELECT COUNT(*) AS null_country_keys
FROM fact_income
WHERE country_id IS NULL;

SELECT COUNT(*) AS null_age_keys
FROM fact_income
WHERE age_id IS NULL;

SELECT COUNT(*) AS null_sex_keys
FROM fact_income
WHERE sex_id IS NULL;

SELECT COUNT(*) AS null_unit_keys
FROM fact_income
WHERE unit_id IS NULL;

SELECT COUNT(*) AS null_statinfo_keys
FROM fact_income
WHERE statinfo_id IS NULL;

SELECT COUNT(*) AS null_years
FROM fact_income
WHERE year IS NULL;

SELECT COUNT(*) AS null_income_values
FROM fact_income
WHERE income IS NULL;

-- ==========================================================
-- SECTION 7: YEAR RANGE VALIDATION
-- ==========================================================

SELECT
	MIN(year) AS first_year,
	MAX(year) AS last_year,
	COUNT(DISTINCT year) AS distinct_years
FROM fact_income;

-- ==========================================================
-- SECTION 8: NEGATIVE OR SUSPICIOUS INCOMES
-- ==========================================================

SELECT *
FROM fact_income
WHERE income < 0;

-- ==========================================================
-- SECTION 9: FLAG DISTRIBUTION
-- ==========================================================

SELECT
	flag,
	COUNT(*) AS observations
FROM fact_income
GROUP BY flag
ORDER BY flag, observations DESC NULLS LAST;

-- ==========================================================
-- SECTION 10: COUNTRY COVERAGE
-- ==========================================================

SELECT COUNT(DISTINCT country_id) AS countries_in_fact
FROM fact_income;

-- ==========================================================
-- SECTION 11: AGE COVERAGE
-- ==========================================================

SELECT COUNT(DISTINCT age_id) AS age_groups_in_fact
FROM fact_income;

-- ==========================================================
-- SECTION 12: INCOME SUMMARY STATISTICS
-- ==========================================================

SELECT
	MIN(income) AS min_income,
	MAX(income) AS max_income,
	ROUND(AVG(income)) AS avg_income,
	PERCENTILE_CONT(0.5)
	WITHIN GROUP (ORDER BY income) AS median_income
FROM fact_income
WHERE income IS NOT NULL;

-- ==========================================================
-- SECTION 13: FACT TABLE GRAIN VALIDATION
-- ==========================================================
-- Expected grain:
-- One row per
-- country × age × sex × unit × statinfo × year

SELECT
	COUNT(*) AS duplicate_grain_rows
FROM (
	SELECT
		country_id,
		age_id,
		sex_id,
		unit_id,
		statinfo_id,
		year,
		COUNT(*)
	FROM
		fact_income
	GROUP BY
		country_id,
		age_id,
		sex_id,
		unit_id,
		statinfo_id,
		year
	HAVING COUNT(*) > 1
) t;

-- ==========================================================
-- END OF VALIDATION
-- ==========================================================
