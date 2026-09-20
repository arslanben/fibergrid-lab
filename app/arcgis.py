"""ArcGIS REST service emulation for the KAPSAMA_VEKTOR MapServer.

Mirrors the REST surface of ArcGIS Server 10.8.1 closely enough for the
portal and its API consumers, including the layer query interface.
"""
import json
import logging
from decimal import Decimal

from flask import Blueprint, Response, render_template, request

import db

log = logging.getLogger("fibergrid.arcgis")

bp = Blueprint("arcgis", __name__, url_prefix="/arcgis")

CURRENT_VERSION = 10.81
MAX_RECORD_COUNT = 2000

LAYER_FIELDS = [
    {"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "OBJECTID",
     "sqlType": "sqlTypeInteger", "domain": None, "editable": False,
     "nullable": False, "length": 10},
    {"name": "IL", "type": "esriFieldTypeString", "alias": "İl",
     "sqlType": "sqlTypeNVarchar", "domain": None, "editable": False,
     "nullable": True, "length": 40},
    {"name": "ILCE", "type": "esriFieldTypeString", "alias": "İlçe",
     "sqlType": "sqlTypeNVarchar", "domain": None, "editable": False,
     "nullable": True, "length": 60},
    {"name": "MAHALLE", "type": "esriFieldTypeString", "alias": "Mahalle",
     "sqlType": "sqlTypeNVarchar", "domain": None, "editable": False,
     "nullable": True, "length": 80},
    {"name": "BANT", "type": "esriFieldTypeString", "alias": "Bant",
     "sqlType": "sqlTypeNVarchar", "domain": None, "editable": False,
     "nullable": True, "length": 20},
    {"name": "KAPASITE", "type": "esriFieldTypeInteger", "alias": "Kapasite (Mbps)",
     "sqlType": "sqlTypeInteger", "domain": None, "editable": False,
     "nullable": True, "length": 10},
    {"name": "DURUM", "type": "esriFieldTypeString", "alias": "Durum",
     "sqlType": "sqlTypeNVarchar", "domain": None, "editable": False,
     "nullable": True, "length": 20},
    {"name": "LON", "type": "esriFieldTypeDouble", "alias": "Boylam",
     "sqlType": "sqlTypeFloat", "domain": None, "editable": False,
     "nullable": True, "length": 8},
    {"name": "LAT", "type": "esriFieldTypeDouble", "alias": "Enlem",
     "sqlType": "sqlTypeFloat", "domain": None, "editable": False,
     "nullable": True, "length": 8},
]

FIELD_NAMES = {field["name"] for field in LAYER_FIELDS}
DEFAULT_SELECT = "objectid, il, ilce, mahalle, bant, kapasite, durum, lon, lat"

SERVICES_DIRECTORY = {
    "currentVersion": CURRENT_VERSION,
    "folders": ["Utilities"],
    "services": [{"name": "KAPSAMA_VEKTOR", "type": "MapServer"}],
}

UTILITIES_DIRECTORY = {
    "currentVersion": CURRENT_VERSION,
    "folders": [],
    "services": [{"name": "PrintingTools", "type": "GPServer"}],
}


def _convert(value):
    """psycopg returns Decimal for numeric columns; JSON needs int/float."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _json(data, pretty: bool = False) -> Response:
    if pretty:
        body = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return Response(body + "\n", mimetype="application/json")


def _pretty() -> bool:
    return request.args.get("f", "").lower() == "pjson"


def _error(message: str, details: list | None = None, code: int = 400) -> Response:
    return _json({"error": {"code": code, "message": message,
                            "details": details or []}})


def _parse_out_fields(raw: str) -> list[str] | None:
    if not raw or raw == "*":
        return [name for name in FIELD_NAMES]
    names = [part.strip().upper() for part in raw.split(",") if part.strip()]
    if not names or any(name not in FIELD_NAMES for name in names):
        return None
    return names


@bp.get("/rest/info")
def rest_info():
    return _json({"currentVersion": CURRENT_VERSION,
                  "owningSystemUrl": request.host_url.rstrip("/")},
                 _pretty())


@bp.get("/rest/services")
def services_directory():
    f = request.args.get("f", "html").lower()
    if f in ("json", "pjson"):
        return _json(SERVICES_DIRECTORY, f == "pjson")
    return render_template("arcgis_services.html")


@bp.get("/rest/services/Utilities")
def utilities_directory():
    f = request.args.get("f", "html").lower()
    if f in ("json", "pjson"):
        return _json(UTILITIES_DIRECTORY, f == "pjson")
    return render_template("arcgis_services.html", utilities=True)


@bp.get("/rest/services/Utilities/PrintingTools")
def printing_tools():
    data = {
        "currentVersion": CURRENT_VERSION,
        "serviceDescription": "PrintingTools",
        "hasVersionedData": False,
        "supportsDisconnectedEditing": False,
        "hasStaticData": False,
        "maxRecordCount": 1000,
        "supportedQueryFormats": "JSON",
        "capabilities": "Uploads,Execution",
        "description": "Yazdırma görevleri (Export Web Map)",
        "copyrightText": "© Lodos Telekom A.Ş.",
        "spatialReference": {"wkid": 4326, "latestWkid": 4326},
        "initialExtent": {
            "xmin": 25.6, "ymin": 35.8, "xmax": 44.8, "ymax": 42.1,
            "spatialReference": {"wkid": 4326, "latestWkid": 4326},
        },
        "fullExtent": {
            "xmin": 25.6, "ymin": 35.8, "xmax": 44.8, "ymax": 42.1,
            "spatialReference": {"wkid": 4326, "latestWkid": 4326},
        },
        "allowGeometryUpdates": False,
        "units": "esriDecimalDegrees",
        "tasks": ["Export Web Map"],
        "executionType": "esriExecutionTypeSynchronous",
        "parameters": [],
        "layers": [],
        "tables": [],
    }
    return _json(data, _pretty())


@bp.get("/rest/services/KAPSAMA_VEKTOR/MapServer")
def mapserver_metadata():
    data = {
        "currentVersion": CURRENT_VERSION,
        "serviceDescription": "FWA kapsama alanı yayın servisi",
        "hasVersionedData": False,
        "supportsDisconnectedEditing": False,
        "hasStaticData": False,
        "hasSharedDomains": False,
        "maxRecordCount": MAX_RECORD_COUNT,
        "supportedQueryFormats": "JSON, geoJSON, PBF",
        "supportsVCSProjection": False,
        "supportedExportFormats": "csv,shapefile,sqlite,geoPackage,filegdb,featureCollection,geojson",
        "capabilities": "Map,Query,Data",
        "description": "Lodos Telekom FWA kapsama vektörleri",
        "copyrightText": "© Lodos Telekom A.Ş.",
        "spatialReference": {"wkid": 4326, "latestWkid": 4326},
        "initialExtent": {
            "xmin": 25.6, "ymin": 35.8, "xmax": 44.8, "ymax": 42.1,
            "spatialReference": {"wkid": 4326, "latestWkid": 4326},
        },
        "fullExtent": {
            "xmin": 25.6, "ymin": 35.8, "xmax": 44.8, "ymax": 42.1,
            "spatialReference": {"wkid": 4326, "latestWkid": 4326},
        },
        "allowGeometryUpdates": False,
        "units": "esriDecimalDegrees",
        "layers": [{
            "id": 0,
            "name": "FWA_KAPSAMA",
            "parentLayerId": -1,
            "defaultVisibility": True,
            "subLayerIds": None,
            "minScale": 0,
            "maxScale": 0,
            "type": "Feature Layer",
            "geometryType": "esriGeometryPoint",
        }],
        "tables": [],
    }
    return _json(data, _pretty())


@bp.get("/rest/services/KAPSAMA_VEKTOR/MapServer/0")
def layer_metadata():
    data = {
        "currentVersion": CURRENT_VERSION,
        "id": 0,
        "name": "FWA_KAPSAMA",
        "type": "Feature Layer",
        "description": "FWA (Fixed Wireless Access) kapsama noktaları",
        "geometryType": "esriGeometryPoint",
        "sourceSpatialReference": {"wkid": 4326, "latestWkid": 4326},
        "objectIdField": "OBJECTID",
        "globalIdField": "",
        "displayField": "MAHALLE",
        "typeIdField": "",
        "fields": LAYER_FIELDS,
        "capabilities": "Query",
        "supportsAdvancedQueries": True,
        "advancedQueryCapabilities": {
            "useStandardizedQueries": False,
            "supportsPagination": True,
            "supportsTrueCurve": True,
            "supportsReturningQueryExtent": True,
            "supportsStatistics": True,
            "supportsOrderBy": True,
            "supportsDistinct": True,
        },
        "hasM": False,
        "hasZ": False,
        "maxRecordCount": MAX_RECORD_COUNT,
        "supportsDatumTransformation": True,
        "supportedQueryFormats": "JSON, geoJSON, PBF",
    }
    return _json(data, _pretty())


@bp.get("/rest/services/KAPSAMA_VEKTOR/MapServer/0/query")
def layer_query():
    where = (request.args.get("where") or "1=1").strip() or "1=1"
    pretty = _pretty()

    if request.args.get("returnCountOnly", "false").lower() == "true":
        try:
            row = db.fetch_one(
                f"SELECT COUNT(*) AS cnt FROM cbs.fwa_noktalar WHERE ({where})")
        except Exception as exc:  # noqa: BLE001 - generic service error
            log.warning("query failed where=%r error=%s", where, exc)
            return _error("Unable to complete operation.",
                          ["Query execution failed."])
        return _json({"count": int(row["cnt"])}, pretty)

    if request.args.get("returnIdsOnly", "false").lower() == "true":
        try:
            rows = db.fetch_all(
                f"SELECT objectid FROM cbs.fwa_noktalar WHERE ({where}) "
                f"ORDER BY objectid LIMIT {MAX_RECORD_COUNT}")
        except Exception as exc:  # noqa: BLE001
            log.warning("query failed where=%r error=%s", where, exc)
            return _error("Unable to complete operation.",
                          ["Query execution failed."])
        return _json({"objectIdFieldName": "OBJECTID",
                      "objectIds": [int(row["objectid"]) for row in rows]},
                     pretty)

    fields = _parse_out_fields(request.args.get("outFields", "*"))
    if fields is None:
        return _error("Invalid or missing input parameters.",
                      ["Invalid field name in outFields."])

    try:
        limit = int(request.args.get("resultRecordCount", 100))
    except ValueError:
        return _error("Invalid or missing input parameters.",
                      ["resultRecordCount must be an integer."])
    limit = max(1, min(limit, MAX_RECORD_COUNT))

    order_by = (request.args.get("orderByFields") or "OBJECTID").strip().upper()
    if order_by not in FIELD_NAMES:
        return _error("Invalid or missing input parameters.",
                      [f"Invalid orderByFields value: {order_by}"])

    select_list = ", ".join(sorted(fields, key=lambda n: list(FIELD_NAMES).index(n)))
    return_geometry = request.args.get("returnGeometry", "true").lower() == "true"

    try:
        rows = db.fetch_all(
            f"SELECT {select_list} FROM cbs.fwa_noktalar WHERE ({where}) "
            f"ORDER BY {order_by} LIMIT %s", (limit,))
    except Exception as exc:  # noqa: BLE001
        log.warning("query failed where=%r error=%s", where, exc)
        return _error("Unable to complete operation.",
                      ["Query execution failed."])

    features = []
    for row in rows:
        attributes = {name: _convert(row[name.lower()]) for name in fields}
        feature = {"attributes": attributes}
        if return_geometry and "LON" in fields and "LAT" in fields:
            feature["geometry"] = {"x": _convert(row["lon"]),
                                   "y": _convert(row["lat"])}
        features.append(feature)

    data = {
        "objectIdFieldName": "OBJECTID",
        "uniqueIdField": {"name": "OBJECTID", "isSystemMaintained": True},
        "globalIdFieldName": "",
        "geometryType": "esriGeometryPoint",
        "spatialReference": {"wkid": 4326, "latestWkid": 4326},
        "fields": [field for field in LAYER_FIELDS if field["name"] in fields],
        "features": features,
    }
    return _json(data, pretty)
