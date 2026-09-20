# Architecture and design notes

## Components

| Service | Image | Role |
|---|---|---|
| `waf` | Python 3.12 + Flask/gunicorn + requests | reverse proxy with F5 ASM-style value inspection; the only published port |
| `app` | Python 3.12 + Flask/gunicorn + psycopg | ArcGIS-style REST emulation, GIS portal and `/webservice/api/*` |
| `db` | PostgreSQL 16 (alpine) | Oracle-compatible data layer (`--locale=C`) |

Networks: `dmz` (waf ↔ app) and `internal` (app ↔ db, `internal: true`).
The database is never exposed to the host unless the `docker-compose.debug.yml`
override is used for maintenance.

## Fidelity: original engagement → this lab

| Original engagement | This lab |
|---|---|
| Internal fiber/GIS portal of a telecom operator | portal at `localhost:8080` ("Lodos Telekom / FiberGrid GIS") |
| ArcGIS Server 10.8.1, MapServer layer 0 | emulated REST surface: `currentVersion: 10.81`, matching JSON shapes and error objects |
| Standardized queries disabled | the query builder concatenates `where` into the SQL statement |
| Oracle instance and planning schema | PostgreSQL database `lds_gisdb`, quoted role `"CBS"`, Oracle-compat layer |
| Oracle dictionary views | `TAB`, `COL`, `ALL_USERS`, `DATABASE_PROPERTIES` recreated in schema `cbs` |
| F5 ASM value-based signatures | `waf/waf.py` rule list with the same blocked vocabulary |
| Unpublished route and staging tables | renamed for this lab as `GUZERGAH` and `A90312` |
| Unauthenticated archive download endpoint | `/webservice/api/Export?file=` keeps the same weakness |
| Large coverage and route inventories | 118,427 FWA rows, 742,318 route rows (deterministic seed) |

All identifiers in this lab are fictional variants; the internal names of the
original engagement are deliberately not reproduced.

## Oracle compatibility layer

`DECODE(expr, search, result, default)` is defined three times (numeric,
double precision, text) because PostgreSQL's `SIGN(integer)` returns
`double precision`, while integer expressions elsewhere resolve to `numeric`.
`SIGN(integer)` is redefined in schema `cbs` so the arithmetic stays in the
integer domain, like Oracle's. `NVL` and `SYS_GUID()` are trivial wrappers,
and `cbs.dual` plus the `ALL_USERS.CREATED` / `DATABASE_PROPERTIES.DESCRIPTION`
columns keep the dictionary shapes close to Oracle's.

`GREATEST`/`LEAST` are parser constructs in PostgreSQL and cannot be shadowed
by functions, so ordering uses PostgreSQL's NULL-ignoring `GREATEST`. Every
extraction target in the data set is non-NULL, which keeps the blind
arithmetic identical to the original Oracle behaviour.

The database is initialised with `--locale=C`, so `MIN`/`MAX`/`GREATEST` on
text compare byte-wise (ASCII order), matching Oracle's default binary sort.
Text columns involved in comparisons also carry `COLLATE "C"` explicitly.

## Data model

```
sde.fwa_nokta_verisi    118,427 rows   published coverage points
cbs.fwa_noktalar          view           what the public layer actually reads
cbs.guzergah              742,318 rows   internal fiber routes (unpublished)
cbs.a90312              2 rows         staging notes (unpublished)
cbs.tab / cbs.col         views          dictionary views for schema cbs
cbs.all_users            view           Oracle-style account list (with CREATED)
cbs.database_properties  view           includes GLOBAL_DB_NAME = LDS_GISDB
cbs.dual                 view           Oracle's single-row DUAL table
```

The seed is deterministic (`db/init/04_seed.sql`, `random.seed` in
`app/tools/gen_export.py`), so every deployment behaves identically.

## WAF rules

`waf/waf.py` normalises each parameter (up to three percent-decoding passes,
like an appliance) and applies the deployed signature list. Beyond the
boolean keywords, comments and dictionary names seen in the original
engagement, the profile also blocks the ordering, pattern and positional
helpers that would otherwise bypass the intended technique:

- boolean/set keywords: `AND`, `OR`, `LIKE`, `ILIKE`, `SIMILAR`, `REGEXP*`,
  `UNION`, `EXEC`, `WAITFOR`, `EXISTS`, `BETWEEN`
- aggregation and shape: `COUNT(`, leading `(SELECT`, leading `SELECT`
- string/position helpers: `ASCII(`, `SUBSTR(`, `SUBSTRING`, `INSTR(`,
  `TRANSLATE(`, `POSITION`, `STRPOS`, `STARTS_WITH`, `SPLIT_PART`, `LEFT(`,
  `RIGHT(`, `LPAD(`, `RPAD(`, `OVERLAY`, `REPLACE(`, `TRIM(`/`LTRIM(`/
  `RTRIM(`/`BTRIM(`
- row limiting and PostgreSQL-only operators: `LIMIT`, `FETCH`, `OFFSET`,
  `^@`, `@@`, `to_tsvector`, `to_tsquery`
- dictionary names: `ALL_TABLES`, `ALL_OBJECTS`, `GLOBAL_NAME`,
  `SYS_CONTEXT`, `ORA_DATABASE_NAME`, `ROWNUM`, `V$DATABASE`
- database fingerprinting: `information_schema`, `pg_catalog`, `pg_*`,
  `current_database(`, `current_setting(`, `current_schema`, `version(`
- time/OOB primitives: `SLEEP(`, `BENCHMARK(`, `DBMS_*`, `UTL_*`
- comments/separators: `--`, `/*`, `#`, `;`
- comparison/pattern/escape abuse: `<`, `>`, `~`, `\`

Blocked requests receive the appliance-style page with a random support ID.
The rules are deliberately lexical: arithmetic and equality-based subqueries
pass, which is the core lesson of the lab.

`WAF_BLOCK_STATUS` (default `200`, the F5 default) can be set to `403` if you
prefer a conventional status code.

## Extending the lab

- **More layers:** add a service entry to `SERVICES_DIRECTORY` in
  `app/arcgis.py` and a matching metadata handler.
- **Harder WAF:** append signatures to `waf/waf.py` (for example `DECODE(`),
  but keep at least one arithmetic path available.
- **Different data volume:** adjust `generate_series(...)` limits in
  `db/init/04_seed.sql`; extraction time scales with the number of requests,
  not with the table size.
- **Re-theme:** the scenario lives in `app/templates/*`, `app/webservice.py`
  and the SQL seed; nothing else depends on the branding.
