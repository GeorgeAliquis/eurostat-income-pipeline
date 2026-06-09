/*
==========================================================
EUROSTAT INCOME DISTRIBUTION EDA
==========================================================

Dataset: Eurostat – Income distribution by age, sex, country

Goal:
Exploratory analysis of income distribution across EU countries
using SQL (PostgreSQL-style) to demonstrate:

- Window functions (LAG, ROW_NUMBER, RANK)
- Aggregations and cohort filtering
- Time-series comparisons
- Gender and age-group inequality analysis
- Percentile-based distribution analysis

Notes:
- All queries assume pre-cleaned view: vw_income_analysis
- Focus is on reproducible analytical patterns rather than ETL
*/

-- ==========================================================
-- 1. DATASET OVERVIEW
-- ==========================================================

SELECT
	MIN(year) AS first_year,
	MAX(year) AS last_year,
	COUNT(DISTINCT year) AS years_covered
	
FROM vw_income_analysis;


SELECT
	COUNT(DISTINCT country_code) AS countries,
	COUNT(DISTINCT age_group) AS age_groups,
	COUNT(DISTINCT sex) AS sex_categories,
	COUNT(DISTINCT unit) AS units,
	COUNT(DISTINCT statinfo) AS statistics
	
FROM vw_income_analysis;

-- ==========================================================
-- 2. DATA QUALITY EXPLORATION
-- ==========================================================

SELECT
	flag,
	COUNT(*) AS observations
FROM vw_income_analysis
GROUP BY flag
ORDER BY flag, observations DESC NULLS LAST;


SELECT
	country_name,
	COUNT(*) AS missing_income_rows
FROM vw_income_analysis
WHERE income IS NULL
GROUP BY country_name
ORDER BY missing_income_rows DESC;

-- ==========================================================
-- 3. TOP COUNTRIES BY PURCHASING POWER STANDARD (PPS)
-- ==========================================================

SELECT
    country_name,
    year AS available_year,
    income
FROM (
    SELECT
        country_name,
        year,
        income,
        ROW_NUMBER() OVER (
            PARTITION BY country_name
            ORDER BY year DESC
        ) AS rn
    FROM vw_income_analysis
    WHERE
        age_group = 'TOTAL'
        AND sex = 'T'
        AND statinfo = 'MEAN_EI'
        AND unit = 'PPS'
        AND is_country = TRUE
        AND income IS NOT NULL
) t
WHERE rn = 1
ORDER BY income DESC
LIMIT 10;

-- ==========================================================
-- 4. BOTTOM COUNTRIES BY PURCHASING POWER STANDARD (PPS)
-- ==========================================================

SELECT
    country_name,
    year AS available_year,
    income
FROM (
    SELECT
        country_name,
        year,
        income,
        ROW_NUMBER() OVER (
            PARTITION BY country_name
            ORDER BY year DESC
        ) AS rn
    FROM vw_income_analysis
    WHERE
        age_group = 'TOTAL'
        AND sex = 'T'
        AND statinfo = 'MEAN_EI'
        AND unit = 'PPS'
        AND is_country = TRUE
        AND income IS NOT NULL
) t
WHERE rn = 1
ORDER BY income
LIMIT 10;

-- ==========================================================
-- 5. COUNTRY RANKINGS BY MOST RECENT YEAR (PPS)
-- ==========================================================

SELECT
	country_name,
	income,
	RANK() OVER (
		ORDER BY income DESC
	) AS income_rank
FROM vw_income_analysis
WHERE
	year = (
		SELECT MAX(year)
		FROM vw_income_analysis
	)
	AND age_group = 'TOTAL'
	AND sex = 'T'
	AND statinfo = 'MEAN_EI'
	AND unit = 'PPS'
	AND is_country = TRUE;

-- ==========================================================
-- 6. GENDER INCOME GAP (MEDIAN | IN EUROS)
-- ==========================================================

WITH ranked AS (
    SELECT
        country_name,
        year,
        sex,
        income,
        ROW_NUMBER() OVER (
            PARTITION BY country_name, sex
            ORDER BY year DESC
        ) AS rn
    FROM vw_income_analysis
    WHERE
        age_group = 'TOTAL'
        AND statinfo = 'MED_EI'
        AND unit = 'EUR'
        AND sex IN ('M', 'F')
        AND is_country = TRUE
        AND income IS NOT NULL
),

latest_per_sex AS (
    SELECT *
    FROM ranked
    WHERE rn = 1
),

pivoted AS (
    SELECT
        country_name,

        MAX(CASE WHEN sex = 'M' THEN income END) AS male_income,
        MAX(CASE WHEN sex = 'F' THEN income END) AS female_income,

        MAX(CASE WHEN sex = 'M' THEN year END) AS male_year,
        MAX(CASE WHEN sex = 'F' THEN year END) AS female_year
    FROM latest_per_sex
    GROUP BY country_name
)

SELECT
    country_name,
	
    -- pick the most recent available year between the two sexes
    GREATEST(male_year, female_year) AS available_year,

    male_income,
    female_income,

    ROUND(
        (male_income - female_income)::numeric,
        2
    ) AS income_gap

FROM pivoted

ORDER BY income_gap DESC NULLS LAST;

-- ==========================================================
-- 7. AGE GROUP ANALYSIS (AVERAGE | IN EUROS)
-- ==========================================================

SELECT
	age_label,
	ROUND(AVG(income)::numeric, 2) AS average_income
FROM vw_income_analysis
WHERE
	year = (
		SELECT MAX(year)
		FROM vw_income_analysis
	)
	AND sex = 'T'
	AND statinfo = 'MEAN_EI'
	AND unit = 'EUR'
	AND is_country = TRUE
	
GROUP BY age_label
ORDER BY average_income DESC NULLS LAST;

-- ==========================================================
-- 8. YOUNG VS ELDERLY POPULATIONS (AVERAGE | IN EUROS)
-- ==========================================================

SELECT
	country_name,
	age_label,
	income
FROM vw_income_analysis
WHERE
	age_group IN (
		'Y16-24',
		'Y_GE65'
	)
	AND sex = 'T'
	AND statinfo = 'MEAN_EI'
	AND unit = 'EUR'
	AND is_country = TRUE
	AND year = (
		SELECT MAX(year)
		FROM vw_income_analysis
	)
ORDER BY country_name;

-- ==========================================================
-- 9. MEAN VS MEDIAN INCOME (IN EUROS)
-- ==========================================================

WITH valid_years AS (
    SELECT
        country_name,
        year
    FROM vw_income_analysis
    WHERE
        age_group = 'TOTAL'
        AND sex = 'T'
        AND unit = 'EUR'
        AND is_country = TRUE
        AND statinfo IN ('MEAN_EI', 'MED_EI')
        AND income IS NOT NULL
    GROUP BY country_name, year
    HAVING COUNT(DISTINCT statinfo) = 2
),

latest_year AS (
    SELECT DISTINCT ON (country_name)
        country_name,
        year
    FROM valid_years
    ORDER BY country_name, year DESC
),

filtered AS (
    SELECT a.*
    FROM vw_income_analysis a
    JOIN latest_year y
      ON a.country_name = y.country_name
     AND a.year = y.year
    WHERE
        a.age_group = 'TOTAL'
        AND a.sex = 'T'
        AND a.unit = 'EUR'
        AND a.is_country = TRUE
        AND a.statinfo IN ('MEAN_EI', 'MED_EI')
)

SELECT
    country_name,
	MAX(year) AS available_year,

    MAX(CASE WHEN statinfo = 'MEAN_EI' THEN income END) AS mean_income,
    MAX(CASE WHEN statinfo = 'MED_EI' THEN income END) AS median_income

FROM filtered
GROUP BY country_name
ORDER BY mean_income DESC NULLS LAST;

-- ==========================================================
-- 10. YEAR-OVER-YEAR CHANGE (AVERAGE | IN EUROS)
-- ==========================================================

SELECT
	country_name,
	year,
	income,

	income
	-
	LAG(income)
	OVER (
    	PARTITION BY country_name
    	ORDER BY year
	) AS yearly_change

FROM vw_income_analysis

WHERE
	age_group = 'TOTAL'
	AND sex = 'T'
	AND statinfo = 'MEAN_EI'
	AND unit = 'EUR'
	AND is_country = TRUE;

-- ==========================================================
-- 11. LONG-TERM COUNTRY GROWTH (MEDIAN | IN PPS)
-- ==========================================================

SELECT
	country_name,

	ROUND(
		(MAX(income)
		-
		MIN(income)
	)
    /
    MIN(income)
    * 100
) AS growth_percentage

FROM vw_income_analysis

WHERE
	age_group = 'TOTAL'
	AND sex = 'T'
	AND statinfo = 'MED_EI'
	AND unit = 'PPS'
	AND is_country = TRUE

GROUP BY country_name

ORDER BY growth_percentage DESC;

-- ==========================================================
-- 12. BEST PERFORMING COUNTRY EACH YEAR (MEDIAN | IN PPS)
-- ==========================================================

WITH ranked AS (

SELECT
    year,
    country_name,
    income,

    ROW_NUMBER()
    OVER (
        PARTITION BY year
        ORDER BY income DESC NULLS LAST
    ) AS rn

FROM vw_income_analysis

WHERE
    age_group = 'TOTAL'
    AND sex = 'T'
    AND statinfo = 'MED_EI'
    AND unit = 'PPS'
    AND is_country = TRUE

)

SELECT
	year,
	country_name AS best_performing_country,
	income
FROM ranked
WHERE rn = 1
ORDER BY year;

-- ==========================================================
-- 13. INCOME DISTRIBUTION SUMMARY (IN EURO)
-- ==========================================================

SELECT
	MIN(income) AS minimum_income,
	MAX(income) AS maximum_income,
	ROUND(AVG(income)::numeric, 2) AS average_income,

	PERCENTILE_CONT(0.25)
    	WITHIN GROUP (ORDER BY income)
    	AS p25,

	PERCENTILE_CONT(0.50)
    	WITHIN GROUP (ORDER BY income)
    	AS median,

	PERCENTILE_CONT(0.75)
    	WITHIN GROUP (ORDER BY income)
    	AS p75

FROM vw_income_analysis

WHERE
	income IS NOT NULL
	AND unit = 'EUR';

-- ==========================================================
-- END OF EDA
-- ==========================================================
