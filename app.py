import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'leads.json')
GHL_API_KEY     = os.environ.get('GHL_API_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2NhdGlvbl9pZCI6Ik1PNUtHaVNQVEpTMEk0MVdLMm9qIiwidmVyc2lvbiI6MSwiaWF0IjoxNzU3MTAwODIwMzQwLCJzdWIiOiJGaHFWZGJRMTRPT2lacTI5aUh2SiJ9.jM57d0uU31Uc0dQ7lwIkwxk8QFfBTnWdfPOSpy21S3A')
GHL_LOCATION_ID = os.environ.get('GHL_LOCATION_ID', 'MO5KGiSPTJS0I41WK2oj')
GHL_API_URL     = 'https://rest.gohighlevel.com/v1/contacts/'


def load_leads():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return []


def save_lead(lead):
    leads = load_leads()
    leads.append(lead)
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(leads, f, indent=2)


def push_to_ghl(lead):
    if not GHL_API_KEY:
        logger.warning('GHL_API_KEY not set, skipping GHL push')
        return False
    situation = lead.get('situation', '')
    tags = ['Bo Knows Houses', 'Website Lead', 'Website Lead - Bo Knows Houses']
    if situation:
        tags.append(situation)
    payload = {
        'firstName': lead.get('name', '').split()[0] if lead.get('name') else '',
        'lastName': ' '.join(lead.get('name', '').split()[1:]) if lead.get('name') else '',
        'email': lead.get('email', ''),
        'phone': lead.get('phone', ''),
        'tags': tags,
        'address1': lead.get('address', ''),
        'city':     lead.get('city', ''),
        'state':    lead.get('state', ''),
        'postalCode': lead.get('zip', ''),
        'source': 'Website - Bo Knows Houses',
    }
    if GHL_LOCATION_ID:
        payload['locationId'] = GHL_LOCATION_ID
    headers = {
        'Authorization': 'Bearer ' + GHL_API_KEY,
        'Content-Type': 'application/json',
    }
    try:
        resp = requests.post(GHL_API_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info('GHL push success: %s', resp.status_code)
        return True
    except Exception as e:
        logger.error('GHL push failed: %s', str(e))
        return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')


@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')


@app.route('/submit', methods=['POST'])
def submit():
    lead = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'address': request.form.get('address', '').strip(),
        'city': request.form.get('city', '').strip(),
        'state': request.form.get('state', '').strip(),
        'zip': request.form.get('zip', '').strip(),
        'condition': request.form.get('condition', '').strip(),
        'situation': request.form.get('situation', '').strip(),
        'name': request.form.get('name', '').strip(),
        'phone': request.form.get('phone', '').strip(),
        'email': request.form.get('email', '').strip(),
        'source_page': request.form.get('source_page', 'unknown'),
    }
    save_lead(lead)
    push_to_ghl(lead)
    try:
        import sys
        sys.path.insert(0, '/Users/robertzinno/.openclaw/workspace/boknowshouses-leads')
        from twilio_sms import send_sms
        msg = (f"🏠 NEW SELLER LEAD — Bo Knows Houses\n"
               f"Name: {lead.get('name','')}\n"
               f"Phone: {lead.get('phone','')}\n"
               f"Property: {lead.get('address','')}, {lead.get('city','')}, {lead.get('state','')} {lead.get('zip','')}\n"
               f"Condition: {lead.get('condition','')}\n"
               f"Situation: {lead.get('situation','')}")
        send_sms(msg)
    except Exception as e:
        logger.error('SMS error: %s', str(e))
    return redirect(url_for('thank_you'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5052, debug=False)
