-- staging.stg_geolocation
-- Technique: CTE, aggregation, AVG, COUNT — collapse many lat/lng per zip
BEGIN;

TRUNCATE staging.stg_geolocation;

INSERT INTO staging.stg_geolocation (
    zip_code_prefix,
    avg_lat,
    avg_lng,
    city,
    state,
    point_count
)
WITH cleaned AS (
    SELECT
        LPAD(REGEXP_REPLACE(TRIM(geolocation_zip_code_prefix), '[^0-9]', '', 'g'), 5, '0')
            AS zip_code_prefix,
        NULLIF(TRIM(geolocation_lat), '')::NUMERIC(12, 8)   AS lat,
        NULLIF(TRIM(geolocation_lng), '')::NUMERIC(12, 8)   AS lng,
        LOWER(TRIM(geolocation_city))                       AS city,
        UPPER(TRIM(geolocation_state))                      AS state
    FROM raw.olist_geolocation
    WHERE NULLIF(TRIM(geolocation_zip_code_prefix), '') IS NOT NULL
),
ranked_city AS (
    -- Mode-ish: most frequent city/state per zip for label
    SELECT
        zip_code_prefix,
        city,
        state,
        ROW_NUMBER() OVER (
            PARTITION BY zip_code_prefix
            ORDER BY COUNT(*) DESC, city, state
        ) AS rn
    FROM cleaned
    GROUP BY zip_code_prefix, city, state
)
SELECT
    c.zip_code_prefix,
    AVG(c.lat)::NUMERIC(12, 8)  AS avg_lat,
    AVG(c.lng)::NUMERIC(12, 8)  AS avg_lng,
    rc.city,
    rc.state,
    COUNT(*)::INTEGER           AS point_count
FROM cleaned c
JOIN ranked_city rc
  ON rc.zip_code_prefix = c.zip_code_prefix
 AND rc.rn = 1
WHERE c.lat IS NOT NULL
  AND c.lng IS NOT NULL
GROUP BY c.zip_code_prefix, rc.city, rc.state;

COMMIT;
