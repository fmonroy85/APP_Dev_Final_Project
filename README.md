# APP_Dev_Final_Project

TravelMed Concierge — Flask Backend

A single-traveler medical concierge app for searching clinics and health services across Europe.

FHIR R4 medical concierge application using:
- HL7 FHIR R4 at `https://r4.smarthealthit.org`
- EU Open Data Portal SPARQL at `https://data.europa.eu/sparql`

## Getting started

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python app.py
   ```
4. Open in the browser:
   ```
   http://127.0.0.1:5000
   ```

## Configuration

Set optional environment variables before running:

- `SECRET_KEY` — Flask secret key
- `FHIR_BASE_URL` — FHIR server base URL (default: `https://r4.smarthealthit.org`)
- `FHIR_TIMEOUT` — FHIR request timeout seconds (default: `12`)
- `SPARQL_URL` — SPARQL endpoint URL (default: `https://data.europa.eu/sparql`)
- `SPARQL_TIMEOUT` — SPARQL request timeout seconds (default: `15`)
- `TRAVEL_REGION` — travel region for clinic search (default: `Europe`)
- `TRAVELER_NAME` — traveler name shown in the app UI (default: `Traveling user`)
- `FLASK_DEBUG` — set to `1` to enable Flask debug mode
- `PORT` — port to bind the Flask server (default: `5000`)

## Available files

- `app.py` — main Flask application and API routes
- `requirements.txt` — Python dependencies
- `templates/index.html` — homepage view
- `.gitignore` — ignored files for development

## Notes

This starter app includes clinic discovery using SPARQL and FHIR patient/resource routes for a medical concierge workflow.
