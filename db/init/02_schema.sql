-- FiberGrid CTF - schemas and base tables.

CREATE SCHEMA sde;   -- published feature data (ArcGIS "publisher" schema)
CREATE SCHEMA cbs;    -- CBS planning schema (internal, mostly unpublished)

-- Base geometry table behind the published KAPSAMA_VEKTOR layer.
-- The public REST layer reads it through cbs.fwa_noktalar (created in 03_compat.sql).
CREATE TABLE sde.fwa_nokta_verisi (
    objectid  numeric PRIMARY KEY,
    il        text,
    ilce      text,
    mahalle   text,
    bant      text,
    kapasite  numeric,
    durum     text,
    lon       numeric,
    lat       numeric
);

-- Internal route inventory. Columns follow the CBS planning conventions.
CREATE TABLE cbs.guzergah (
    objectid numeric PRIMARY KEY,
    id       text COLLATE "C",
    adi      text COLLATE "C",
    notlar   text COLLATE "C"
);

-- Import/staging table used by the FTTH_ENVANTER batch jobs.
CREATE TABLE cbs.a90312 (
    aciklama text COLLATE "C",
    durum    text COLLATE "C"
);
