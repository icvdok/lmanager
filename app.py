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
    matching_locations = []  # Initialize list to store matching locations
    if prefix is not None:
        # Loop through the locations and log any location name that starts with the identified prefix
        for location in locations:
            if location['name'].startswith(prefix):
                logging.debug(f'f_Location found: {location["name"]}')
                matching_locations.append(location['name'])  # Add matching location to the list
                # Extract the number after the prefix and update highest_number if it's greater
                try:
                    number = int(location['name'][len(prefix):])
                    if number > highest_number:
                        highest_number = number
                except ValueError:
                    logging.warning(f'f_Invalid number format in location name: {location["name"]}')
        
        # Sort matching locations progressively
        matching_locations.sort(key=lambda x: int(x[len(prefix):]))
    else:
        logging.debug(f'f_No valid prefix found for selected type {selected_type}.')

    return highest_number, matching_locations

def generate_new_locations(matching_locations, num_new_locations, highest_number):
    new_locations = []
    existing_numbers = [int(loc.split('_')[1]) for loc in matching_locations]
    
    # Find gaps in the existing sequence
    all_numbers = set(range(1, highest_number + num_new_locations + 1))
    unused_numbers = sorted(all_numbers - set(existing_numbers))
    
    # Generate new locations to fill gaps first
    for i in range(min(num_new_locations, len(unused_numbers))):
        new_locations.append(f's_{unused_numbers[i]}')
    
    # If there are still new locations to create, continue from the highest number
    next_number = highest_number + 1
    while len(new_locations) < num_new_locations:
        new_locations.append(f's_{next_number}')
        next_number += 1
    
    return new_locations

# def create_new_location(next_number, parent_location_id):
#     new_location_name = f'gb_{next_number}'
#     description = 'gridfinity_bin'
#     location_type_index = 4  # Use the pk for '_gridfinity_bin'
    
#     url = f'{base_url}stock/location/'
#     data = {
#         'name': new_location_name,
#         'description': description,
#         'parent': parent_location_id,
#         'location_type': location_type_index  # Updated field name
#     }
#     response = requests.post(url, headers=headers, json=data)
#     if response.status_code == 201:
#         return {
#             'message': f'New location "{new_location_name}" with description "{description}" and location type index "{location_type_index}" created successfully under parent location ID {parent_location_id}.'
#         }
#     else:
#         return {
#             'message': f'Failed to create new location. Status code: {response.status_code}',
#             'details': response.json()
#         }

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

def create_new_locations(new_locations, parent_location_name, selected_type, location_types):
    # Define the description rules
    description_rules = {
        'bin': 'gridfinity bin',
        'sorter': 'sorter organizer',
        'box': 'box contenitore',
        'shelf': 'shelf armadio'
    }

    # Ensure selected_type is not empty
    if not selected_type:
        logging.error('Selected type is empty')
        return

    # Find the type name for the selected type
    type_name = None
    for location_type in location_types:
        if location_type['pk'] == int(selected_type):
            type_name = location_type['name']
            break

    if type_name is None:
        logging.error(f'Invalid selected type: {selected_type}')
        return

    # Find the description for the selected type
    description = description_rules.get(type_name, '')

    # Get the parent location ID from its name
    response = requests.get(f'{base_url}stock/location/', headers=headers, params={'name': parent_location_name})
    if response.status_code != 200:
        logging.error(f'Failed to get parent location ID: {response.text}')
        return

    # Log the API response for debugging
    logging.debug(f'API response: {response.json()}')

    # Check if the response is empty
    if not response.json():
        logging.error(f'No location found with name: {parent_location_name}')
        return

    parent_location_id = response.json()[0]['pk']

    # Log the new locations to be created
    for location in new_locations:
        data = {
            'name': location,
            'description': description,
            'parent': parent_location_id,
            'type': selected_type
        }
        logging.info(f'Would create location: {data}')
        # Uncomment the following lines to enable actual creation
        # response = requests.post(f'{base_url}stock/location/', headers=headers, json=data)
        # if response.status_code == 201:
        #     logging.info(f'Successfully created location: {location}')
        # else:
        #     logging.error(f'Failed to create location: {location}, response: {response.text}')

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
        if 'create_locations' in request.form:
            parent_location_name = request.form.get('parent_location_name')
            selected_type = request.form.get('location_type')
            num_new_locations = int(request.form.get('num_new_locations'))
            logging.debug(f'r_Selected parent location: {parent_location_name}')
            logging.debug(f'r_Selected location type: {selected_type}')
            logging.debug(f'r_How many locations: {num_new_locations}')

            # Find the highest progressive number and matching locations for the selected type
            highest_number, matching_locations = find_highest_progressive_number(locations, location_types, selected_type)
            logging.debug(f'r_highest_number identified: {highest_number}')
            logging.debug(f'r_matching_locations identified: {matching_locations}')
            
            # Calculate the next available progressive number
            next_number = highest_number + 1
            logging.debug(f'r_next_number is: {next_number}')
            
            # Generate new locations
            new_locations = generate_new_locations(matching_locations, num_new_locations, highest_number)
            logging.debug(f'r_new_locations to create: {new_locations}')
            
            # Combine and sort all locations progressively
            all_locations = matching_locations + new_locations
            all_locations.sort(key=lambda x: int(x.split('_')[1]))
            
            return render_template('slcreate.html', locations=locations, highest_number=highest_number, next_number=next_number, location_types=location_types, all_locations=all_locations, new_locations=new_locations, parent_location_name=parent_location_name, selected_type=selected_type, num_new_locations=num_new_locations)
        
        elif 'execute_creation' in request.form:
            new_locations = request.form.getlist('new_locations')
            parent_location_name = request.form.get('parent_location_name')
            selected_type = request.form.get('location_type')
            create_new_locations(new_locations, parent_location_name, selected_type, location_types)
            return redirect(url_for('slcreate'))

    return render_template('slcreate.html', locations=locations, highest_number=0, next_number=1, location_types=location_types, all_locations=[], new_locations=[], parent_location_name='', selected_type='', num_new_locations=1)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5556, debug=True)
