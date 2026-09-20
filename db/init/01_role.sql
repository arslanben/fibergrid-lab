-- FiberGrid CTF - application database role.
-- The GIS backend connects as "CBS" (Oracle style, uppercase quoted role).
\getenv cbs_password CBS_PASSWORD
CREATE ROLE "CBS" LOGIN PASSWORD :'cbs_password';
ALTER ROLE "CBS" SET default_transaction_read_only = on;
ALTER ROLE "CBS" SET search_path TO cbs, public, pg_catalog;
