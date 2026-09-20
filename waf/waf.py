"""F5 ASM-style value inspection layer.

Sits in front of the FiberGrid application and rejects requests whose
parameters match the SQL-injection signature set configured on the
production appliance. Blocked requests receive the standard "Request
Rejected" response page.

The signature list mirrors the profile that was active in production:
value-based patterns for boolean keywords, aggregation, blocked scalar
functions, dictionary view names and comment/separator abuse.
"""
import logging
import os
import random
import re
import urllib.parse

import requests
from flask import Flask, Response, request
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UPSTREAM = os.environ.get("UPSTREAM", "http://app:8000").rstrip("/")
BLOCK_STATUS = int(os.environ.get("WAF_BLOCK_STATUS", "200"))
MAX_VALUE_LENGTH = 4096

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("fibergrid.waf")

# No static files in the appliance: keep Flask's built-in /static route from
# shadowing the catch-all proxy route.
app = Flask(__name__, static_folder=None)

# Docker's embedded DNS can fail transiently right after a container is
# recreated; retry connection-level errors so the proxy never returns a
# spurious 502.
SESSION = requests.Session()
_RETRY = Retry(total=3, connect=3, read=2, status=0, backoff_factor=0.25,
               allowed_methods=None)
SESSION.mount("http://", HTTPAdapter(max_retries=_RETRY))

RULES = [
    # boolean / set keywords
    (r"\bAND\b", "SQLI-KW-AND"),
    (r"\bOR\b", "SQLI-KW-OR"),
    (r"\bLIKE\b", "SQLI-KW-LIKE"),
    (r"\bILIKE\b", "SQLI-KW-ILIKE"),
    (r"\bSIMILAR\b", "SQLI-KW-SIMILAR"),
    (r"\bREGEXP\w*", "SQLI-KW-REGEXP"),
    (r"\bUNION\b", "SQLI-KW-UNION"),
    (r"\bEXEC(UTE)?\b", "SQLI-KW-EXEC"),
    (r"\bWAITFOR\b", "SQLI-KW-WAITFOR"),
    (r"\bEXISTS\b", "SQLI-KW-EXISTS"),
    (r"\bBETWEEN\b", "SQLI-OP-BETWEEN"),
    # aggregation / subquery shape
    (r"COUNT\s*\(", "SQLI-AGG-COUNT"),
    (r"^\s*\(\s*SELECT\b", "SQLI-SUBQ-LEADING"),
    (r"^\s*SELECT\b", "SQLI-SUBQ-START"),
    # blocked scalar functions (substring / position helpers)
    (r"\bASCII\s*\(", "SQLI-FN-ASCII"),
    (r"\bSUBSTR\s*\(", "SQLI-FN-SUBSTR"),
    (r"\bSUBSTRING\b", "SQLI-FN-SUBSTRING"),
    (r"\bINSTR\s*\(", "SQLI-FN-INSTR"),
    (r"\bTRANSLATE\s*\(", "SQLI-FN-TRANSLATE"),
    (r"\bPOSITION\b", "SQLI-FN-POSITION"),
    (r"\bSTRPOS\b", "SQLI-FN-STRPOS"),
    (r"\bSTARTS_WITH\b", "SQLI-FN-STARTS_WITH"),
    (r"\bSPLIT_PART\b", "SQLI-FN-SPLIT_PART"),
    (r"\bLEFT\s*\(", "SQLI-FN-LEFT"),
    (r"\bRIGHT\s*\(", "SQLI-FN-RIGHT"),
    # row limiting (PostgreSQL syntax)
    (r"\bLIMIT\b", "PG-KW-LIMIT"),
    (r"\bFETCH\b", "PG-KW-FETCH"),
    (r"\bOFFSET\b", "PG-KW-OFFSET"),
    # PostgreSQL string/prefix helpers usable as equality oracles
    (r"\^@", "PG-OP-PREFIX"),
    (r"\bOVERLAY\b", "PG-FN-OVERLAY"),
    (r"\bREPLACE\s*\(", "PG-FN-REPLACE"),
    (r"\bLPAD\s*\(", "PG-FN-LPAD"),
    (r"\bRPAD\s*\(", "PG-FN-RPAD"),
    (r"\bTRIM\s*\(", "PG-FN-TRIM"),
    (r"\bLTRIM\s*\(", "PG-FN-LTRIM"),
    (r"\bRTRIM\s*\(", "PG-FN-RTRIM"),
    (r"\bBTRIM\s*\(", "PG-FN-BTRIM"),
    (r"\bTO_TSVECTOR\b", "PG-FN-TSVECTOR"),
    (r"\bTO_TSQUERY\b", "PG-FN-TSQUERY"),
    (r"\bPLAINTO_TSQUERY\b", "PG-FN-PLAINTO_TSQUERY"),
    (r"@@", "PG-OP-TSMATCH"),
    # Oracle dictionary objects
    (r"\bALL_TABLES\b", "SQLI-DICT-ALL_TABLES"),
    (r"\bALL_OBJECTS\b", "SQLI-DICT-ALL_OBJECTS"),
    (r"\bGLOBAL_NAME\b", "SQLI-DICT-GLOBAL_NAME"),
    (r"\bSYS_CONTEXT\b", "SQLI-DICT-SYS_CONTEXT"),
    (r"\bORA_DATABASE_NAME\b", "SQLI-DICT-ORA_DATABASE_NAME"),
    (r"\bROWNUM\b", "SQLI-DICT-ROWNUM"),
    (r"\bV\$DATABASE\b", "SQLI-DICT-V_DATABASE"),
    # database fingerprinting
    (r"\bINFORMATION_SCHEMA\b", "DBFP-INFO_SCHEMA"),
    (r"\bPG_CATALOG\b", "DBFP-PG_CATALOG"),
    (r"\bPG_\w+", "DBFP-PG_PREFIX"),
    (r"\bCURRENT_DATABASE\s*\(", "DBFP-CURRENT_DB"),
    (r"\bCURRENT_SETTING\s*\(", "DBFP-CURRENT_SETTING"),
    (r"\bCURRENT_SCHEMA\b", "DBFP-CURRENT_SCHEMA"),
    (r"\bVERSION\s*\(", "DBFP-VERSION"),
    # time-based / out-of-band primitives
    (r"\bSLEEP\s*\(", "SQLI-TIME-SLEEP"),
    (r"\bBENCHMARK\s*\(", "SQLI-TIME-BENCHMARK"),
    (r"\bDBMS_\w+", "ORA-PKG-DBMS"),
    (r"\bUTL_\w+", "ORA-PKG-UTL"),
    # comments and separators
    (r"-{2,}", "SQLI-CMT-DOUBLE_DASH"),
    (r"/\*", "SQLI-CMT-BLOCK_OPEN"),
    (r"\*/", "SQLI-CMT-BLOCK_CLOSE"),
    (r";", "SQLI-SEP-SEMICOLON"),
    (r"#", "SQLI-CMT-HASH"),
    # comparison / pattern / escape abuse
    (r"<", "SQLI-CMP-LT"),
    (r">", "SQLI-CMP-GT"),
    (r"~", "SQLI-CMP-REGEX"),
    (r"\\", "SQLI-ESC-BACKSLASH"),
]

COMPILED = [(re.compile(pattern, re.IGNORECASE), name) for pattern, name in RULES]

BLOCK_PAGE = (
    "<html><head><title>Request Rejected</title></head>"
    "<body>The requested URL was rejected. Please consult with your administrator."
    "<br><br>Your support ID is: {support_id}"
    "<br><br><a href='javascript:history.back();'>[Go Back]</a></body></html>"
)

HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
    "content-length", "accept-encoding", "server", "date",
}


def normalize(value: str) -> str:
    """Decode percent- and plus-encoding repeatedly, like the appliance does."""
    for _ in range(3):
        decoded = urllib.parse.unquote_plus(value)
        if decoded == value:
            break
        value = decoded
    return value


def inspect(value: str) -> str | None:
    if "\x00" in value:
        return "SIG-NULL-BYTE"
    normalized = normalize(value)
    if len(normalized) > MAX_VALUE_LENGTH:
        return "SIG-VALUE-LENGTH"
    for regex, name in COMPILED:
        if regex.search(normalized):
            return name
    return None


def support_id() -> str:
    return "".join(random.choices("0123456789", k=18))


def reject(signature: str, sample: str) -> Response:
    sid = support_id()
    log.warning("BLOCKED signature=%s value=%r support_id=%s",
                signature, sample[:200], sid)
    return Response(
        BLOCK_PAGE.format(support_id=sid),
        status=BLOCK_STATUS,
        content_type="text/html; charset=utf-8",
    )


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "HEAD", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "HEAD", "OPTIONS"])
def proxy(path: str):
    raw_body = request.get_data()

    for name, values in request.args.lists():
        for value in values:
            signature = inspect(value)
            if signature:
                return reject(signature, f"{name}={value}")

    if raw_body:
        try:
            for name, values in request.form.lists():
                for value in values:
                    signature = inspect(value)
                    if signature:
                        return reject(signature, f"{name}={value}")
        except Exception:  # noqa: BLE001 - non-form body
            pass

    headers = {key: value for key, value in request.headers.items()
               if key.lower() not in HOP_HEADERS}
    headers["Host"] = request.host

    url = UPSTREAM + request.full_path.rstrip("?")
    try:
        upstream = SESSION.request(request.method, url, headers=headers,
                                   data=raw_body, timeout=30,
                                   allow_redirects=False)
    except requests.RequestException as exc:
        log.error("upstream error: %s", exc)
        return Response("Service unavailable\n", status=502,
                        content_type="text/plain")

    response = Response(upstream.content, upstream.status_code)
    for key, value in upstream.headers.items():
        if key.lower() not in HOP_HEADERS:
            response.headers[key] = value
    # The appliance-facing "Server" header is set at the WSGI server layer
    # (see gunicorn.conf.py); WSGI-level Server headers are dropped by gunicorn.
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
