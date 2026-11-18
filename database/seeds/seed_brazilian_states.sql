-- =============================================================================
-- Seed: Brazilian state abbreviations → name + region
-- Used by dim_geography enrichment.
-- Safe to re-run.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS analytics.seed_brazilian_states (
    state_code  CHAR(2)     NOT NULL,
    state_name  TEXT        NOT NULL,
    region      TEXT        NOT NULL,
    CONSTRAINT pk_seed_brazilian_states PRIMARY KEY (state_code)
);

TRUNCATE analytics.seed_brazilian_states;

INSERT INTO analytics.seed_brazilian_states (state_code, state_name, region) VALUES
    ('AC', 'Acre',                'North'),
    ('AL', 'Alagoas',             'Northeast'),
    ('AP', 'Amapá',               'North'),
    ('AM', 'Amazonas',            'North'),
    ('BA', 'Bahia',               'Northeast'),
    ('CE', 'Ceará',               'Northeast'),
    ('DF', 'Distrito Federal',    'Central-West'),
    ('ES', 'Espírito Santo',      'Southeast'),
    ('GO', 'Goiás',               'Central-West'),
    ('MA', 'Maranhão',            'Northeast'),
    ('MT', 'Mato Grosso',         'Central-West'),
    ('MS', 'Mato Grosso do Sul',  'Central-West'),
    ('MG', 'Minas Gerais',        'Southeast'),
    ('PA', 'Pará',                'North'),
    ('PB', 'Paraíba',             'Northeast'),
    ('PR', 'Paraná',              'South'),
    ('PE', 'Pernambuco',          'Northeast'),
    ('PI', 'Piauí',               'Northeast'),
    ('RJ', 'Rio de Janeiro',      'Southeast'),
    ('RN', 'Rio Grande do Norte', 'Northeast'),
    ('RS', 'Rio Grande do Sul',   'South'),
    ('RO', 'Rondônia',            'North'),
    ('RR', 'Roraima',             'North'),
    ('SC', 'Santa Catarina',      'South'),
    ('SP', 'São Paulo',           'Southeast'),
    ('SE', 'Sergipe',             'Northeast'),
    ('TO', 'Tocantins',           'North');

COMMIT;
