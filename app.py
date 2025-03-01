from flask import Flask, request, jsonify, render_template, redirect, url_for
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

# Define the location type configuration
location_type_config = {
    1: {'prefix': 'a_', 'description': 'shelf armadio'},  # Shelf
    2: {'prefix': 'b_', 'description': 'box contenitore'},  # Box
    3: {'prefix': 's_', 'description': 'sorter organizer'},  # Sorter
    4: {'prefix': 'g_', 'description': 'gridfinity bin'}   # Bin
}

# Function to get all locations
def get_all_locations():
    logging.debug('f_call function get_all_location')
    url = f'{base_url}stock/location/'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return []
# Function to get sublocations by parent ID
def get_sublocations(parent_id):
    logging.debug('f_call function get_sublocations')
    url = f'{base_url}stock/location/'
    response = requests.get(url, headers=headers, params={'parent': parent_id})
    if response.status_code == 200:
        return response.json()
    return []
# Function to find the list of sublocation from a given parent
def move_sublocations(sublocations, target_parent_id):
    logging.debug('f_call function move_sublocations')
    url = f'{base_url}stock/location/'
    for sublocation in sublocations:
        sublocation_id = sublocation['pk']
        data = {'parent': target_parent_id}
        response = requests.patch(f'{url}{sublocation_id}/', headers=headers, json=data)
        if response.status_code != 200:
            logging.error(f'Failed to move sublocation {sublocation_id}. Status code: {response.status_code}')
    return sublocations

def find_highest_progressive_number(locations, location_types, selected_type):
    logging.debug('f_call function find_highest_progressive_number')
    logging.debug(f'f_Location types provided: {location_types}')
    logging.debug(f'f_Selected type provided: {selected_type}')

    # Get the configuration for the selected type
    config = location_type_config.get(int(selected_type))
    if not config:
        logging.error(f'f_No configuration found for selected type: {selected_type}')
        return 0, []

    prefix = config['prefix']
    logging.debug(f'f_Prefix: {prefix}')

    # Find matching locations
    matching_locations = [loc['name'] for loc in locations if loc['name'].startswith(prefix)]
    logging.debug(f'f_Matching locations: {matching_locations}')

    # Filter out invalid location names
    valid_locations = []
    for loc in matching_locations:
        try:
            # Extract the number part and ensure it's an integer
            int(loc[len(prefix):])
            valid_locations.append(loc)
        except ValueError:
            logging.warning(f'f_Invalid number format in location name: {loc}')

    logging.debug(f'f_Valid locations: {valid_locations}')

    # Sort valid locations by their numeric suffix
    valid_locations.sort(key=lambda x: int(x[len(prefix):]))

    # Find the highest number
    highest_number = max([int(loc[len(prefix):]) for loc in valid_locations], default=0)
    logging.debug(f'f_Highest number: {highest_number}')

    return highest_number, valid_locations

def generate_new_locations(matching_locations, num_new_locations, highest_number, selected_type):
    logging.debug('f_call function generate_new_locations')
    new_locations = []

    # Get the configuration for the selected type
    config = location_type_config.get(int(selected_type))
    if not config:
        logging.error(f'f_No configuration found for selected type: {selected_type}')
        return new_locations

    prefix = config['prefix']

    existing_numbers = [int(loc.split('_')[1]) for loc in matching_locations]
    
    # Find gaps in the existing sequence
    all_numbers = set(range(1, highest_number + num_new_locations + 1))
    unused_numbers = sorted(all_numbers - set(existing_numbers))
    
    # Generate new locations to fill gaps first
    for i in range(min(num_new_locations, len(unused_numbers))):
        new_locations.append(f'{prefix}{unused_numbers[i]:04d}')
    
    # If there are still new locations to create, continue from the highest number
    next_number = highest_number + 1
    while len(new_locations) < num_new_locations:
        new_locations.append(f'{prefix}{next_number:04d}')
        next_number += 1
    
    return new_locations

def get_location_types():
    logging.debug('f_call function get_location_types')
    url = f'{base_url}stock/location-type/'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        location_types = response.json()
        # Filter out "room" and "home" location types
        filtered_location_types = [lt for lt in location_types if lt['name'].lower() not in ['room', 'home']]
        return filtered_location_types
    else:
        return {
            'message': f'Failed to retrieve location types. Status code: {response.status_code}',
            'details': response.json()
        }

def create_new_locations(locations, new_locations, parent_location_name, selected_type, location_types):
    logging.debug('f_call function create_new_locations')

    # Ensure selected_type is not empty
    if not selected_type:
        logging.error('f_Selected type is empty')
        return

    # Get the configuration for the selected type
    config = location_type_config.get(int(selected_type))
    if not config:
        logging.error(f'f_No configuration found for selected type: {selected_type}')
        return

    prefix = config['prefix']
    description = config['description']

    # Find the parent location ID from the existing locations collection using the pathstring field
    parent_location_id = next((loc['pk'] for loc in locations if loc['pathstring'] == parent_location_name), None)
    if parent_location_id is None:
        logging.error(f'f_No location found with name: {parent_location_name}')
        return

    # Log the new locations to be created
    for location in new_locations:
        data = {
            'name': location,
            'description': description,
            'parent': parent_location_id,
            'location_type': int(selected_type)  # Ensure this is correctly set as a number
        }

        logging.info(f'f_Would create location: {data}')
        # Uncomment the following lines to enable actual creation
        response = requests.post(f'{base_url}stock/location/', headers=headers, json=data)
        if response.status_code == 201:
            logging.info(f'Successfully created location: {location}')
        else:
            logging.error(f'Failed to create location: {location}, response: {response.text}')

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
    logging.debug('r_Locations function executed')
    
    # Get the list of location types
    location_types = get_location_types()
    logging.debug('r_Location types function executed')

    if request.method == 'POST':
        if 'create_locations' in request.form:
            logging.debug(f'r_submit_click')
            parent_location_name = request.form.get('parent_location_name')
            selected_type = request.form.get('location_type')
            num_new_locations = int(request.form.get('num_new_locations'))
            logging.debug(f'r_Selected parent location: {parent_location_name}')
            logging.debug(f'r_Selected location type: {selected_type}')
            logging.debug(f'r_Number of locations: {num_new_locations}')

            # Find the highest progressive number and matching locations for the selected type
            highest_number, matching_locations = find_highest_progressive_number(locations, location_types, selected_type)
            logging.debug(f'r_Highest number identified: {highest_number}')
            logging.debug(f'r_Matching locations identified: {matching_locations}')
            
            # Calculate the next available progressive number
            next_number = highest_number + 1
            logging.debug(f'r_Next number is: {next_number}')
            
            # Generate new locations > location that match with the standard prefix, how many locations are needed, the first highest progressive number available for the new location
            new_locations = generate_new_locations(matching_locations, num_new_locations, highest_number, selected_type)
            logging.debug(f'r_New locations to create: {new_locations}')
            
            # Combine and sort all locations progressively
            all_locations = matching_locations + new_locations
            all_locations.sort(key=lambda x: int(x.split('_')[1]))
            
            return render_template('slcreate.html', locations=locations, highest_number=highest_number, next_number=next_number, location_types=location_types, all_locations=all_locations, new_locations=new_locations, parent_location_name=parent_location_name, selected_type=selected_type, num_new_locations=num_new_locations)
        
        elif 'execute_creation' in request.form:
            logging.debug(f'r_execute_click')
            new_locations = request.form.getlist('new_locations')
            parent_location_name = request.form.get('parent_location_name')
            selected_type = request.form.get('location_type')
            create_new_locations(locations, new_locations, parent_location_name, selected_type, location_types)
            return redirect(url_for('slcreate'))

    return render_template('slcreate.html', locations=locations, highest_number=0, next_number=1, location_types=location_types, all_locations=[], new_locations=[], parent_location_name='', selected_type='', num_new_locations=1)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5556, debug=True)
