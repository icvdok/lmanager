from flask import Flask, request, jsonify, render_template
import requests
import json
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Get the API token and base URL from environment variables
api_token = os.getenv('INVENTREE_API_TOKEN')
base_url = os.getenv('BASE_URL')

# Set up the headers with your API token
headers = {
    'Authorization': f'Token {api_token}',
    'Content-Type': 'application/json'
}

# Function to get all locations
def get_all_locations():
    logging.debug('call function get_all_location')
    url = f'{base_url}stock/location/'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

# Function to get sublocations by parent ID
def get_sublocations(parent_id):
    logging.debug('call function get_sublocations')
    url = f'{base_url}stock/location/'
    response = requests.get(url, headers=headers, params={'parent': parent_id})
    if response.status_code == 200:
        return response.json()
    return []

# Function to move sublocations to a new parent location
def move_sublocations(sublocations, target_parent_id, simulate):
    logging.debug('call function move_sublocations')
    url = f'{base_url}stock/location/'
    if simulate:
        logging.info(f'Simulating move of {len(sublocations)} sublocations to parent ID {target_parent_id}')
        return [{'pk': sublocation['pk'], 'pathstring': sublocation['pathstring'], 'simulated': True} for sublocation in sublocations]
    else:
        for sublocation in sublocations:
            sublocation_id = sublocation['pk']
            data = {'parent': target_parent_id}
            response = requests.patch(f'{url}{sublocation_id}/', headers=headers, json=data)
            if response.status_code != 200:
                logging.error(f'Failed to move sublocation {sublocation_id}. Status code: {response.status_code}')
        return sublocations

@app.route('/', methods=['GET', 'POST'])
def index():
    locations = get_all_locations()
    sublocations = []
    if request.method == 'POST':
        source_location_parent = request.form.get('source_location_parent')
        target_location_parent = request.form.get('target_location_parent')
        simulate = request.form.get('simulate') == 'true'
        selected_location = next((loc for loc in locations if loc['pathstring'] == source_location_parent), None)
        target_location = next((loc for loc in locations if loc['pathstring'] == target_location_parent), None)
        if selected_location and target_location:
            sublocations = get_sublocations(selected_location['pk'])
            sublocations = move_sublocations(sublocations, target_location['pk'], simulate)
    return render_template('index.html', locations=locations, sublocations=sublocations, simulate=simulate)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5556, debug=True)