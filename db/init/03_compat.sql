-- FiberGrid CTF - Oracle compatibility layer.
--
-- The production platform runs on Oracle. This lab emulates the subset of
-- Oracle behaviour that the application and its query interface rely on:
-- DECODE / NVL / SYS_GUID / GREATEST(null-propagation) and the dictionary
-- views TAB, COL, ALL_USERS, DATABASE_PROPERTIES.
--
-- Text columns that participate in query comparisons use the "C" collation
-- so MIN/MAX/GREATEST ordering matches Oracle's binary (ASCII) sort order.

-- DECODE(expr, search, result, default)
-- Three overloads cover the arithmetic shapes used by query predicates:
-- numeric columns, SIGN() output (double precision in PostgreSQL) and text.
CREATE OR REPLACE FUNCTION cbs.decode(numeric, numeric, numeric, numeric)
RETURNS numeric LANGUAGE sql IMMUTABLE AS
$$ SELECT CASE WHEN $1 IS NOT DISTINCT FROM $2 THEN $3 ELSE $4 END $$;

CREATE OR REPLACE FUNCTION cbs.decode(double precision, double precision, numeric, numeric)
RETURNS numeric LANGUAGE sql IMMUTABLE AS
$$ SELECT CASE WHEN $1 IS NOT DISTINCT FROM $2 THEN $3 ELSE $4 END $$;

CREATE OR REPLACE FUNCTION cbs.decode(text, text, numeric, numeric)
RETURNS numeric LANGUAGE sql IMMUTABLE AS
$$ SELECT CASE WHEN $1 IS NOT DISTINCT FROM $2 THEN $3 ELSE $4 END $$;

-- NVL(expr, default)
CREATE OR REPLACE FUNCTION cbs.nvl(text, text)
RETURNS text LANGUAGE sql IMMUTABLE AS
$$ SELECT COALESCE($1, $2) $$;

CREATE OR REPLACE FUNCTION cbs.nvl(numeric, numeric)
RETURNS numeric LANGUAGE sql IMMUTABLE AS
$$ SELECT COALESCE($1, $2) $$;

-- SYS_GUID()
CREATE OR REPLACE FUNCTION cbs.sys_guid()
RETURNS text LANGUAGE sql VOLATILE AS
$$ SELECT upper(replace(gen_random_uuid()::text, '-', '')) $$;

-- Note: GREATEST/LEAST are parser constructs in PostgreSQL and cannot be
-- shadowed by a function. This lab therefore uses PostgreSQL's NULL-ignoring
-- GREATEST; every extraction target in the data set is non-NULL, so the
-- blind-extraction arithmetic behaves like the Oracle original.

-- SIGN(integer) -> integer. PostgreSQL's built-in sign() promotes integer
-- input to double precision; the exact-match overload below keeps the
-- arithmetic in the integer domain, as Oracle does.
CREATE OR REPLACE FUNCTION cbs.sign(integer)
RETURNS integer LANGUAGE sql IMMUTABLE AS
$$ SELECT CASE WHEN $1 IS NULL THEN NULL
              WHEN $1 > 0 THEN 1
              WHEN $1 < 0 THEN -1
              ELSE 0 END $$;

-- Published layer view (the ArcGIS service definition points at cbs.FWA_NOKTALAR).
CREATE OR REPLACE VIEW cbs.fwa_noktalar AS
SELECT objectid, il, ilce, mahalle, bant, kapasite, durum, lon, lat
FROM sde.fwa_nokta_verisi;

-- Oracle dictionary views for the CBS planning schema.
CREATE OR REPLACE VIEW cbs.tab AS
SELECT upper(c.relname)::text COLLATE "C" AS tname,
       'TABLE'::text COLLATE "C" AS tabtype,
       0::numeric AS clusterid
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'cbs' AND c.relkind = 'r';

CREATE OR REPLACE VIEW cbs.col AS
SELECT upper(c.relname)::text COLLATE "C" AS tname,
       a.attnum::numeric AS colno,
       upper(a.attname)::text COLLATE "C" AS cname
FROM pg_catalog.pg_attribute a
JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'cbs' AND c.relkind = 'r'
  AND a.attnum > 0 AND NOT a.attisdropped;

-- Oracle's DUAL table (single row, single column).
CREATE OR REPLACE VIEW cbs.dual AS
SELECT 'X'::text COLLATE "C" AS dummy;

CREATE OR REPLACE VIEW cbs.all_users AS
SELECT * FROM (VALUES
    (1::numeric, 'A680241'::text,   TIMESTAMP '2019-03-14 09:12:00'),
    (2::numeric, 'ANONYMOUS'::text, TIMESTAMP '2018-01-01 00:00:00'),
    (3::numeric, 'DBSNMP'::text,    TIMESTAMP '2018-01-01 00:00:00'),
    (4::numeric, 'CBS'::text,       TIMESTAMP '2018-02-19 14:03:00'),
    (5::numeric, 'OUTLN'::text,     TIMESTAMP '2018-01-01 00:00:00'),
    (6::numeric, 'SYS'::text,       TIMESTAMP '2018-01-01 00:00:00'),
    (7::numeric, 'SYSTEM'::text,    TIMESTAMP '2018-01-01 00:00:00')
) AS v(user_id, username, created);

CREATE OR REPLACE VIEW cbs.database_properties AS
SELECT 'GLOBAL_DB_NAME'::text COLLATE "C" AS property_name,
       upper(current_database())::text COLLATE "C" AS property_value,
       'Global database name of the database'::text COLLATE "C" AS description
UNION ALL SELECT 'DB_UNIQUE_NAME'::text, upper(current_database())::text,
       'Unique name of the database'::text
UNION ALL SELECT 'NLS_CHARACTERSET'::text, 'AL32UTF8'::text,
       'Database character set'::text
UNION ALL SELECT 'DEFAULT_TABLESPACE'::text, 'USERS'::text,
       'Name of the default permanent tablespace'::text
UNION ALL SELECT 'DEFAULT_TEMP_TABLESPACE'::text, 'TEMP'::text,
       'Name of the default temporary tablespace'::text;
