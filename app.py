from flask import Flask, render_template, request, jsonify
import os
import requests
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "travelmed-fhir-dev-secret-change-in-prod")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FHIR_BASE_URL      = os.environ.get("FHIR_BASE_URL", "https://r4.smarthealthit.org")
FHIR_TIMEOUT       = int(os.environ.get("FHIR_TIMEOUT", "12"))
SPARQL_URL         = os.environ.get("SPARQL_URL", "https://data.europa.eu/sparql")
SPARQL_TIMEOUT     = int(os.environ.get("SPARQL_TIMEOUT", "15"))
TRAVEL_REGION      = os.environ.get("TRAVEL_REGION", "Europe")
TRAVELER_NAME      = os.environ.get("TRAVELER_NAME", "Traveling user")

# LOINC vital sign codes
VITAL_LOINC = {
    "bp_systolic":  {"code": "8480-6",  "display": "Systolic blood pressure",  "unit": "mmHg",        "ucum": "mm[Hg]"},
    "bp_diastolic": {"code": "8462-4",  "display": "Diastolic blood pressure", "unit": "mmHg",        "ucum": "mm[Hg]"},
    "heart_rate":   {"code": "8867-4",  "display": "Heart rate",               "unit": "beats/min",   "ucum": "/min"},
    "resp_rate":    {"code": "9279-1",  "display": "Respiratory rate",         "unit": "breaths/min", "ucum": "/min"},
    "temperature":  {"code": "8310-5",  "display": "Body temperature",         "unit": "[degF]",      "ucum": "[degF]"},
    "spo2":         {"code": "59408-5", "display": "Oxygen saturation",        "unit": "%",           "ucum": "%"},
    "pain_score":   {"code": "72514-3", "display": "Pain severity - 0-10",     "unit": "{score}",     "ucum": "{score}"},
    "bmi":          {"code": "39156-5", "display": "Body mass index (BMI)",    "unit": "kg/m2",       "ucum": "kg/m2"},
}

# ---------------------------------------------------------------------------
# SPARQL query templates
# ---------------------------------------------------------------------------

# Keyword search — filters by title or description plus a travel region
SPARQL_KEYWORD_QUERY = """\
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT
  ?dataset ?title ?description ?publisher ?theme ?accessURL ?issued
WHERE {{
  ?dataset a dcat:Dataset ;
           dct:title ?title .
  OPTIONAL {{ ?dataset dct:description ?description .
              FILTER(LANG(?description) = 'en') }}
  OPTIONAL {{ ?dataset dct:publisher ?pub .
              ?pub rdfs:label|foaf:name ?publisher .
              FILTER(LANG(?publisher) = 'en' || LANG(?publisher) = '') }}
  OPTIONAL {{ ?dataset dcat:theme ?themeURI .
              ?themeURI skos:prefLabel ?theme .
              FILTER(LANG(?theme) = 'en') }}
  OPTIONAL {{ ?dataset dcat:distribution ?dist .
              ?dist dcat:accessURL ?accessURL }}
  OPTIONAL {{ ?dataset dct:issued ?issued }}
  FILTER(LANG(?title) = 'en')
  FILTER(
    (
      CONTAINS(LCASE(STR(?title)), '{keyword}') ||
      CONTAINS(LCASE(STR(?description)), '{keyword}')
    ) && (
      CONTAINS(LCASE(STR(?title)), '{region}') ||
      CONTAINS(LCASE(STR(?description)), '{region}')
    )
  )
}}
ORDER BY DESC(?issued)
LIMIT {limit}
"""

# Default travel search — health datasets that mention Europe
SPARQL_EUROPE_QUERY = """\
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT
  ?dataset ?title ?description ?publisher ?theme ?accessURL ?issued
WHERE {{
  ?dataset a dcat:Dataset ;
           dct:title ?title .
  OPTIONAL {{ ?dataset dct:description ?description .
              FILTER(LANG(?description) = 'en') }}
  OPTIONAL {{ ?dataset dct:publisher ?pub .
              ?pub rdfs:label|foaf:name ?publisher .
              FILTER(LANG(?publisher) = 'en' || LANG(?publisher) = '') }}
  OPTIONAL {{ ?dataset dcat:theme ?themeURI .
              ?themeURI skos:prefLabel ?theme .
              FILTER(LANG(?theme) = 'en') }}
  OPTIONAL {{ ?dataset dcat:distribution ?dist .
              ?dist dcat:accessURL ?accessURL }}
  OPTIONAL {{ ?dataset dct:issued ?issued }}
  FILTER(LANG(?title) = 'en')
  FILTER(
    (
      CONTAINS(LCASE(STR(?title)), 'health') ||
      CONTAINS(LCASE(STR(?title)), 'hospital') ||
      CONTAINS(LCASE(STR(?title)), 'clinic') ||
      CONTAINS(LCASE(STR(?title)), 'medical') ||
      CONTAINS(LCASE(STR(?title)), 'patient') ||
      CONTAINS(LCASE(STR(?title)), 'care facility')
    ) && (
      CONTAINS(LCASE(STR(?title)), '{region}') ||
      CONTAINS(LCASE(STR(?description)), '{region}')
    )
  )
}}
ORDER BY DESC(?issued)
LIMIT {limit}
"""

# Default health/medical browse — no keyword
SPARQL_HEALTH_QUERY = """\
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT
  ?dataset ?title ?description ?publisher ?theme ?accessURL ?issued
WHERE {{
  ?dataset a dcat:Dataset ;
           dct:title ?title .
  OPTIONAL {{ ?dataset dct:description ?description .
              FILTER(LANG(?description) = 'en') }}
  OPTIONAL {{ ?dataset dct:publisher ?pub .
              ?pub rdfs:label|foaf:name ?publisher .
              FILTER(LANG(?publisher) = 'en' || LANG(?publisher) = '') }}
  OPTIONAL {{ ?dataset dcat:theme ?themeURI .
              ?themeURI skos:prefLabel ?theme .
              FILTER(LANG(?theme) = 'en') }}
  OPTIONAL {{ ?dataset dcat:distribution ?dist .
              ?dist dcat:accessURL ?accessURL }}
  OPTIONAL {{ ?dataset dct:issued ?issued }}
  FILTER(LANG(?title) = 'en')
  FILTER(
    CONTAINS(LCASE(STR(?title)), 'health') ||
    CONTAINS(LCASE(STR(?title)), 'hospital') ||
    CONTAINS(LCASE(STR(?title)), 'clinic') ||
    CONTAINS(LCASE(STR(?title)), 'medical') ||
    CONTAINS(LCASE(STR(?title)), 'pharmaceutical') ||
    CONTAINS(LCASE(STR(?title)), 'patient') ||
    CONTAINS(LCASE(STR(?title)), 'care facility')
  )
}}
ORDER BY DESC(?issued)
LIMIT {limit}
"""

# ---------------------------------------------------------------------------
# SPARQL helpers
# ---------------------------------------------------------------------------

def sparql_query(query: str) -> list:
    """
    Execute a SPARQL SELECT against data.europa.eu/sparql.
    Returns a list of row dicts with plain string values.
    Content negotiation: requests JSON via Accept header.
    """
    resp = requests.get(
        SPARQL_URL,
        params={
            "query":  query,
            "format": "application/sparql-results+json",
        },
        headers={"Accept": "application/sparql-results+json"},
        timeout=SPARQL_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {k: v.get("value", "") for k, v in binding.items()}
        for binding in data.get("results", {}).get("bindings", [])
    ]


def rows_to_clinics(rows: list) -> list:
    """
    Normalise raw SPARQL result rows into frontend-ready clinic dicts.
    Deduplicates on title. Infers a display type from title keywords.
    """
    seen   = set()
    result = []

    for row in rows:
        title = row.get("title", "").strip()
        if not title or title in seen:
            continue
        seen.add(title)

        description = row.get("description", "").strip()
        publisher   = row.get("publisher", "").strip()
        access_url  = row.get("accessURL", "").strip()
        theme       = row.get("theme", "").strip()
        issued      = row.get("issued", "")[:10]
        dataset_uri = row.get("dataset", "").strip()

        t = title.lower()
        if any(k in t for k in ("hospital", "emergency", "er ", "a&e")):
            kind = "Hospital / Emergency"
        elif any(k in t for k in ("clinic", "ambulatory", "outpatient")):
            kind = "Clinic / Ambulatory"
        elif any(k in t for k in ("pharmacy", "pharmaceutical", "drug", "medicine")):
            kind = "Pharmacy / Pharmaceutical"
        elif any(k in t for k in ("mental", "psychiatr", "psychology", "behavioural")):
            kind = "Mental Health"
        elif any(k in t for k in ("primary care", "general practice", "gp ", "family")):
            kind = "Primary Care"
        elif any(k in t for k in ("dental", "dentist", "oral")):
            kind = "Dental"
        elif any(k in t for k in ("cancer", "oncology", "tumour", "tumor")):
            kind = "Oncology"
        else:
            kind = "Health Dataset"

        result.append({
            "id":          dataset_uri or title[:60],
            "title":       title,
            "type":        kind,
            "description": description[:220] + ("…" if len(description) > 220 else ""),
            "publisher":   publisher or "EU Open Data Portal",
            "theme":       theme,
            "access_url":  access_url,
            "issued":      issued,
            "source":      "data.europa.eu/sparql",
            "fhir_resource": "Location",
        })

    return result

# ---------------------------------------------------------------------------
# FHIR helper utilities
# ---------------------------------------------------------------------------

def fhir_get(path: str, params: dict = None) -> dict:
    url  = f"{FHIR_BASE_URL}/{path.lstrip('/') }"
    resp = requests.get(url, params=params or {}, timeout=FHIR_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fhir_post(path: str, resource: dict) -> dict:
    url  = f"{FHIR_BASE_URL}/{path.lstrip('/') }"
    resp = requests.post(
        url,
        json=resource,
        headers={"Content-Type": "application/fhir+json"},
        timeout=FHIR_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def format_name(name_list: list) -> str:
    if not name_list:
        return "Unknown"
    n      = name_list[0]
    given  = " ".join(n.get("given", []))
    family = n.get("family", "")
    return f"{given} {family}".strip() or "Unknown"


def get_codeable_concept(obj: dict) -> str:
    if not obj:
        return "Unknown"
    if "text" in obj:
        return obj["text"]
    for coding in obj.get("coding", []):
        if "display" in coding:
            return coding["display"]
    return "Unknown"


def get_codeable_concept_list(lst: list) -> str:
    return get_codeable_concept(lst[0]) if lst else "Unknown"


def build_observation(patient_id: str, key: str, value: float) -> dict:
    meta = VITAL_LOINC[key]
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                   "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": meta["code"],
                              "display": meta["display"]}], "text": meta["display"]},
        "subject":           {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
        "valueQuantity":     {"value": value, "unit": meta["unit"],
                              "system": "http://unitsofmeasure.org", "code": meta["ucum"]},
    }


def fhir_error(message: str, status: int = 502):
    return jsonify({"error": message, "fhir_base": FHIR_BASE_URL}), status

# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        fhir_base=FHIR_BASE_URL,
        sparql_url=SPARQL_URL,
        traveler_name=TRAVELER_NAME,
        travel_region=TRAVEL_REGION,
    )


@app.route("/health")
def health_check():
    return jsonify({"status": "ok", "app": "TravelMed Concierge",
                    "fhir_base": FHIR_BASE_URL, "sparql_url": SPARQL_URL})

# ---------------------------------------------------------------------------
# Clinic routes — SPARQL powered (data.europa.eu/sparql)
# ---------------------------------------------------------------------------

@app.route("/api/clinics")
def list_clinics():
    """
    Query the EU Open Data Portal SPARQL endpoint for health datasets.

    GET /api/clinics
    GET /api/clinics?q=hospital
    GET /api/clinics?q=pharmacy&limit=10
    GET /api/clinics?region=Germany

    SPARQL endpoint:  data.europa.eu/sparql
    Graph model:      DCAT-AP (dcat:Dataset)
    Returns:          JSON { source, query_type, region, count, results[] }
    """
    keyword = request.args.get("q", "").strip().lower()
    region  = request.args.get("region", TRAVEL_REGION).strip().lower() or TRAVEL_REGION.lower()
    limit   = min(request.args.get("limit", 24, type=int), 50)

    try:
        if keyword:
            query = SPARQL_KEYWORD_QUERY.format(keyword=keyword, region=region, limit=limit)
            query_type = "keyword-region"
        else:
            query = SPARQL_EUROPE_QUERY.format(region=region, limit=limit)
            query_type = "europe-default"

        rows    = sparql_query(query)
        clinics = rows_to_clinics(rows)

        type_filter = request.args.get("type", "").strip().lower()
        if type_filter:
            clinics = [c for c in clinics if type_filter in c["type"].lower()]

        return jsonify({
            "source":       SPARQL_URL,
            "query_type":   query_type,
            "region":       region,
            "keyword":      keyword or None,
            "count":        len(clinics),
            "results":      clinics,
        })

    except requests.Timeout:
        return jsonify({
            "error":   "SPARQL query timed out",
            "source":  SPARQL_URL,
            "results": [],
        }), 504

    except requests.RequestException as exc:
        return jsonify({
            "error":   str(exc),
            "source":  SPARQL_URL,
            "results": [],
        }), 502


@app.route("/api/clinics/sparql-ping")
def sparql_ping():
    """
    Verify connectivity to data.europa.eu/sparql.
    GET /api/clinics/sparql-ping
    """
    test = "SELECT ?s WHERE { ?s a <http://www.w3.org/ns/dcat#Dataset> } LIMIT 1"
    try:
        rows = sparql_query(test)
        return jsonify({"reachable": True, "sparql_url": SPARQL_URL, "rows": len(rows)})
    except requests.RequestException as exc:
        return jsonify({"reachable": False, "sparql_url": SPARQL_URL, "error": str(exc)}), 502


@app.route("/api/clinics/sparql-raw")
def sparql_raw():
    """
    Return the rendered SPARQL query for a given keyword or region (debugging / transparency).
    GET /api/clinics/sparql-raw?q=hospital&region=Europe
    """
    keyword = request.args.get("q", "").strip().lower()
    region  = request.args.get("region", TRAVEL_REGION).strip().lower() or TRAVEL_REGION.lower()
    query   = (SPARQL_KEYWORD_QUERY.format(keyword=keyword, region=region, limit=10)
               if keyword else SPARQL_EUROPE_QUERY.format(region=region, limit=10))
    return jsonify({"sparql_url": SPARQL_URL, "query": query})

# ---------------------------------------------------------------------------
# FHIR Patient routes
# ---------------------------------------------------------------------------

@app.route("/api/fhir/patients/search")
def search_patients():
    """FHIR resource: Patient — search by name"""
    name  = request.args.get("name", "").strip()
    count = request.args.get("count", 20, type=int)
    if not name:
        return jsonify([])
    try:
        bundle = fhir_get("Patient", {"name": name, "_count": count})
    except requests.RequestException:
        return fhir_error("Unable to reach the FHIR server.")
    return jsonify([
        {"id": e["resource"].get("id"),
         "name": format_name(e["resource"].get("name", [])),
         "birthDate": e["resource"].get("birthDate", "Unknown"),
         "gender": e["resource"].get("gender", "Unknown")}
        for e in bundle.get("entry", [])
        if "resource" in e
    ])


@app.route("/api/fhir/patients/<patient_id>")
def get_patient(patient_id):
    """FHIR resource: Patient"""
    try:
        res = fhir_get(f"Patient/{patient_id}")
    except requests.RequestException:
        return fhir_error("Unable to reach the FHIR server.")
    return jsonify({
        "id":        res.get("id"),
        "name":      format_name(res.get("name", [])),
        "birthDate": res.get("birthDate", "Unknown"),
        "gender":    res.get("gender", "Unknown"),
        "address":   res.get("address", []),
        "telecom":   res.get("telecom", []),
    })


@app.route("/api/fhir/patients/<patient_id>/conditions")
def get_conditions(patient_id):
    """FHIR resource: Condition"""
    try:
        bundle = fhir_get("Condition", {"patient": patient_id, "_count": 100})
    except requests.RequestException:
        return fhir_error("Unable to reach the FHIR server.")
    conditions = []
    for entry in bundle.get("entry", []):
        res    = entry.get("resource", {})
        status = res.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "unknown")
        onset  = res.get("onsetDateTime") or res.get("onsetPeriod", {}).get("start", "")
        conditions.append({
            "id":             res.get("id"),
            "display":        get_codeable_concept(res.get("code", {})),
            "clinicalStatus": status,
            "onset":          onset,
            "category":       get_codeable_concept_list(res.get("category", [])),
        })
    return jsonify(conditions)


@app.route("/api/fhir/patients/<patient_id>/medications")
def get_medications(patient_id):
    """FHIR resource: MedicationRequest"""
    status_filter = request.args.get("status", "active")
    try:
        bundle = fhir_get("MedicationRequest", {"patient": patient_id, "status": status_filter, "_count": 50})
    except requests.RequestException:
        return fhir_error("Unable to reach the FHIR server.")
    medications = []
    for entry in bundle.get("entry", []):
        res      = entry.get("resource", {})
        med_name = (get_codeable_concept(res.get("medicationCodeableConcept", {}))
                    if "medicationCodeableConcept" in res
                    else res.get("medicationReference", {}).get("display", "Unknown"))
        dosage = ""
        if res.get("dosageInstruction"):
            di = res["dosageInstruction"][0]
            dosage = di.get("text", "")
            if not dosage:
                dr = di.get("doseAndRate", [{}])[0]
                dq = dr.get("doseQuantity", {})
                if dq.get("value"):
                    dosage = f"{dq['value']} {dq.get('unit','')}"
        medications.append({
            "id":       res.get("id"),
            "name":     med_name,
            "status":   res.get("status", "unknown"),
            "dosage":   dosage,
            "refills":  res.get("dispenseRequest", {}).get("numberOfRepeatsAllowed", 0),
            "authored": res.get("authoredOn", ""),
        })
    return jsonify(medications)


@app.route("/api/fhir/patients/<patient_id>/vitals-summary")
def get_vitals_summary(patient_id):
    """Most recent value per LOINC code. FHIR resource: Observation"""
    try:
        bundle = fhir_get("Observation", {"patient": patient_id, "category": "vital-signs",
                                          "_sort": "-date", "_count": 50})
    except requests.RequestException:
        return fhir_error("Unable to reach the FHIR server.")
    latest = {}
    for entry in bundle.get("entry", []):
        res  = entry.get("resource", {})
        code = res.get("code", {}).get("coding", [{}])[0].get("code", "")
        if code and code not in latest:
            latest[code] = {
                "code":    code,
                "display": get_codeable_concept(res.get("code", {})),
                "value":   res.get("valueQuantity", {}).get("value"),
                "unit":    res.get("valueQuantity", {}).get("unit", ""),
                "date":    res.get("effectiveDateTime", ""),
            }
    return jsonify(list(latest.values()))


@app.route("/api/fhir/patients/<patient_id>/encounters")
def get_encounters(patient_id):
    """FHIR resource: Encounter"""
    count = request.args.get("count", 5, type=int)
    try:
        bundle = fhir_get("Encounter", {"patient": patient_id, "_sort": "-date", "_count": count})
    except requests.RequestException:
        return fhir_error("Unable to reach the FHIR server.")
    encounters = []
    for entry in bundle.get("entry", []):
        res    = entry.get("resource", {})
        period = res.get("period", {})
        cls    = res.get("class", {})
        encounters.append({
            "id":         res.get("id"),
            "status":     res.get("status", "unknown"),
            "class":      cls.get("display") or cls.get("code", "Unknown"),
            "type":       get_codeable_concept_list(res.get("type", [])),
            "reasonCode": get_codeable_concept_list(res.get("reasonCode", [])),
            "start":      period.get("start", ""),
            "end":        period.get("end", ""),
        })
    return jsonify(encounters)


@app.route("/api/fhir/patients/<patient_id>/allergies")
def get_allergies(patient_id):
    """FHIR resource: AllergyIntolerance"""
    try:
        bundle = fhir_get("AllergyIntolerance", {"patient": patient_id, "_count": 50})
    except requests.RequestException:
        return fhir_error("Unable to reach the FHIR server.")
    return jsonify([{
        "id":          e["resource"].get("id"),
        "substance":   get_codeable_concept(e["resource"].get("code", {})),
        "criticality": e["resource"].get("criticality", "unknown"),
        "status":      e["resource"].get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "unknown"),
        "category":    e["resource"].get("category", []),
        "reaction":    [get_codeable_concept(r.get("manifestation", [{}])[0])
                        for r in e["resource"].get("reaction", [])],
    } for e in bundle.get("entry", []) if "resource" in e])


@app.route("/api/fhir/patients/<patient_id>/vitals", methods=["POST"])
def save_vitals(patient_id):
    """Write vital signs as FHIR Observation resources. FHIR resource: Observation"""
    data   = request.get_json(force=True) or {}
    vitals = data.get("vitals", {})
    results = []
    for key in VITAL_LOINC:
        raw = vitals.get(key)
        if raw is None or raw == "":
            continue
        try:
            value = float(raw)
        except (ValueError, TypeError):
            results.append({"vital": key, "status": "skipped"})
            continue
        try:
            resp = fhir_post("Observation", build_observation(patient_id, key, value))
            results.append({"vital": key, "status": "saved", "id": resp.get("id")})
        except requests.RequestException as exc:
            results.append({"vital": key, "status": "error", "message": str(exc)})
    saved = sum(1 for r in results if r["status"] == "saved")
    return jsonify({"success": saved > 0 or not results, "saved": saved,
                    "total": len(results), "results": results, "patient_id": patient_id})


@app.route("/api/fhir/patients/<patient_id>/refill-request", methods=["POST"])
def request_refill(patient_id):
    """Write a new MedicationRequest. FHIR resource: MedicationRequest"""
    data            = request.get_json(force=True) or {}
    medication_name = data.get("medication_name", "Unknown Medication")
    try:
        resp = fhir_post("MedicationRequest", {
            "resourceType": "MedicationRequest",
            "status": "active", "intent": "order",
            "medicationCodeableConcept": {"text": medication_name},
            "subject": {"reference": f"Patient/{patient_id}"},
            "authoredOn": datetime.now(timezone.utc).isoformat(),
            "note": [{"text": "Refill requested via TravelMed Concierge"}],
        })
        return jsonify({"success": True, "medication_request_id": resp.get("id"),
                        "medication_name": medication_name, "patient_id": patient_id})
    except requests.RequestException as exc:
        return fhir_error(f"Refill request failed: {exc}")


@app.route("/api/fhir/patients/<patient_id>/book-appointment", methods=["POST"])
def book_appointment(patient_id):
    """Create a planned Encounter. FHIR resource: Encounter"""
    data        = request.get_json(force=True) or {}
    clinic_name = data.get("clinic_name", "TravelMed Clinic")
    appt_type   = data.get("appointment_type", "ambulatory")
    date_time   = data.get("date_time", datetime.now(timezone.utc).isoformat())
    try:
        resp = fhir_post("Encounter", {
            "resourceType": "Encounter",
            "status": "planned",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
            "type":  [{"text": appt_type}],
            "subject": {"reference": f"Patient/{patient_id}"},
            "period":  {"start": date_time},
            "serviceProvider": {"display": clinic_name},
        })
        return jsonify({"success": True, "encounter_id": resp.get("id"),
                        "clinic_name": clinic_name, "date_time": date_time, "patient_id": patient_id})
    except requests.RequestException as exc:
        return fhir_error(f"Appointment booking failed: {exc}")


@app.route("/api/fhir/metadata")
def fhir_metadata():
    """Proxy FHIR CapabilityStatement."""
    try:
        meta = fhir_get("metadata")
        return jsonify({
            "fhirVersion":   meta.get("fhirVersion", "unknown"),
            "publisher":     meta.get("publisher", "unknown"),
            "status":        meta.get("status", "unknown"),
            "resourceCount": len(meta.get("rest", [{}])[0].get("resource", [])),
        })
    except requests.RequestException:
        return fhir_error("FHIR server unreachable.")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "status": 404}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "status": 500}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port  = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
