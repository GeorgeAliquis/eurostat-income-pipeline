-- ==========================================================
-- EUROSTAT INCOME DATA ANALYTICAL VIEW
-- ==========================================================
-- Grain:
--   One row per country × age × sex × unit × statinfo × year
--
-- Purpose:
--   Provide a denormalized, analyst-friendly view over the
--   dimensional warehouse.
-- ==========================================================

CREATE VIEW vw_income_analysis AS
SELECT
	-- Fact attributes
	f.year,
	f.income,
	f.flag,

	-- Country dimension
	c.country_id,
	c.country_code,
	c.country_name,
	c.is_country,
	c.flag_color,

	-- Age dimension
	a.age_id,
	a.age_group,
	a.age_label,
	a.min_age,
	a.max_age,
	a.age_type,

	-- Sex dimension
	s.sex_id,
	s.sex,
	s.sex_label,

	-- Unit dimension
	u.unit_id,
	u.unit,
	u.unit_label,

	-- Statistic dimension
	st.statinfo_id,
	st.statinfo,
	st.statinfo_label

FROM fact_income f
JOIN dim_country c
USING(country_id)

JOIN dim_age a
USING(age_id)

JOIN dim_sex s
USING(sex_id)

JOIN dim_unit u
USING(unit_id)

JOIN dim_statinfo st
USING(statinfo_id); 
