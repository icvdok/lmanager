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
# Function to find the list of sublocation from a given parent
def move_sublocations(sublocations, target_parent_id):
    logging.debug('call function move_sublocations')
    url = f'{base_url}stock/location/'
    for sublocation in sublocations:
        sublocation_id = sublocation['pk']
        data = {'parent': target_parent_id}
        response = requests.patch(f'{url}{sublocation_id}/', headers=headers, json=data)
        if response.status_code != 200:
            logging.error(f'Failed to move sublocation {sublocation_id}. Status code: {response.status_code}')
    return sublocations
    
def find_highest_progressive_number(locations, location_types, selected_type):
    logging.debug(f'f_Location types provided: {location_types}')
    logging.debug(f'f_Selected type provided: {selected_type}')

    # Define the prefix rules
    prefix_rules = {
        'bin': 'gb_',
        'sorter': 's_',
        'box': 'b_',
        'shelf': 'a_'
    }

    # Find the prefix for the selected type
    prefix = None
    for location_type in location_types:
        if location_type['pk'] == int(selected_type):
            type_name = location_type['name']
            if type_name in prefix_rules:
                prefix = prefix_rules[type_name]
                logging.debug(f'f_Prefix: {prefix}')
            else:
                logging.debug(f'f_Type {type_name} is ignored.')
            break

    highest_number = 0  # Initialize highest_number before the loop
    if prefix is not None:
        # Loop through the locations and log any location name that starts with the identified prefix
        for location in locations:
            if location['name'].startswith(prefix):
                logging.debug(f'f_Location found: {location["name"]}')
                # Extract the number after the prefix and update highest_number if it's greater
                try:
                    number = int(location['name'][len(prefix):])
                    if number > highest_number:
                        highest_number = number
                except ValueError:
                    logging.warning(f'f_Invalid number format in location name: {location["name"]}')
    else:
        logging.debug(f'f_No valid prefix found for selected type {selected_type}.')

    return highest_number

def create_new_location(next_number, parent_location_id):
    new_location_name = f'gb_{next_number}'
    description = 'gridfinity_bin'
    location_type_index = 4  # Use the pk for '_gridfinity_bin'
    
    url = f'{base_url}stock/location/'
    data = {
        'name': new_location_name,
        'description': description,
        'parent': parent_location_id,
        'location_type': location_type_index  # Updated field name
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        return {
            'message': f'New location "{new_location_name}" with description "{description}" and location type index "{location_type_index}" created successfully under parent location ID {parent_location_id}.'
        }
    else:
        return {
            'message': f'Failed to create new location. Status code: {response.status_code}',
            'details': response.json()
        }

def get_location_types():
    url = f'{base_url}stock/location-type/'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        location_types = response.json()
        return location_types
    else:
        return {
            'message': f'Failed to retrieve location types. Status code: {response.status_code}',
            'details': response.json()
        }

@app.route('/', methods=['GET', 'POST'])
def index():
    locations = get_all_locations()
    sublocations = []
    source_location_parent = ''
    target_location_parent = ''

    if request.method == 'POST':
        action = request.form.get('action')
        source_location_parent = request.form.get('source_location_parent')
        target_location_parent = request.form.get('target_location_parent')
        selected_location = next((loc for loc in locations if loc['pathstring'] == source_location_parent), None)
        target_location = next((loc for loc in locations if loc['pathstring'] == target_location_parent), None)

        if action == 'Show Sublocations' and selected_location:
            sublocations = get_sublocations(selected_location['pk'])
        elif action == 'Move Selected Sublocations' and selected_location and target_location:
            selected_sublocations = request.form.getlist('selected_sublocations')
            sublocations = get_sublocations(selected_location['pk'])
            sublocations = [sublocation for sublocation in sublocations if str(sublocation['pk']) in selected_sublocations]
            sublocations = move_sublocations(sublocations, target_location['pk'])

    return render_template('index.html', locations=locations, sublocations=sublocations, source_location_parent=source_location_parent, target_location_parent=target_location_parent)

@app.route('/slcreate', methods=['GET', 'POST'])
def slcreate():
    # Get all locations
    locations = get_all_locations()
    logging.debug('r_locations function executed')
    
    # Get the list of location types
    location_types = get_location_types()
    logging.debug('r_location_types function executed')

    if request.method == 'POST':
        parent_location_name = request.form.get('parent_location_name')
        selected_type = request.form.get('location_type')
        num_new_locations = request.form.get('num_new_locations')
        logging.debug(f'r_Selected parent location: {parent_location_name}')
        logging.debug(f'r_Selected location type: {selected_type}')
        logging.debug(f'r_How many locations: {num_new_locations}')

        # Find the highest progressive number for the selected type
        highest_number = find_highest_progressive_number(locations, location_types, selected_type)
        logging.debug(f'r_highest_number identified: {highest_number}')
        
        # Calculate the next available progressive number
        next_number = highest_number + 1
        logging.debug(f'r_next_number is: {next_number}')
        
        return render_template('slcreate.html', locations=locations, highest_number=highest_number, next_number=next_number, location_types=location_types)

    return render_template('slcreate.html', locations=locations, highest_number=0, next_number=1, location_types=location_types)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5556, debug=True)
