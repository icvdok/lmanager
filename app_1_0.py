from flask import Flask, request, jsonify, render_template
import json
from dotenv import load_dotenv
import os

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
    print(f'call function get_all_location')
    url = f'{base_url}stock/location/'
    response = request.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

# Function to find the highest progressive number
def find_highest_progressive_number(locations):
    highest_number = 0
    print(f'call function find_highest_progressive_number')
    for location in locations:
        name = location['name']
        if name.startswith('gb_'):
            try:
                number = int(name.split('_')[1])
                if number > highest_number:
                    highest_number = number
            except ValueError:
                continue
    return highest_number

# Function to get location ID by name
def get_location_id_by_name(location_name):
    print(f'call function get_location_id_by_name')
    url = f'{base_url}stock/location/'
    response = request.get(url, headers=headers, params={'name': location_name})
    if response.status_code == 200:
        locations = response.json()
        if locations:
            return locations[0]['pk']
    return None

# Function to create a new location with the next available number
def create_new_location(next_number, parent_location_id, simulate):
    print(f'call function create_new_location')
    new_location_name = f'gb_{next_number}'
    description = 'gridfinity_bin'
    location_type_index = 4  # Use the pk for '_gridfinity_bin'
    if simulate:
        return {
            'simulation': True,
            'message': f'New location "{new_location_name}" with description "{description}" and location type index "{location_type_index}" would be created under parent location ID {parent_location_id}.'
        }
    else:
        url = f'{base_url}stock/location/'
        data = {
            'name': new_location_name,
            'description': description,
            'parent': parent_location_id,
            'location_type': location_type_index  # Updated field name
        }
        response = request.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return {
                'simulation': False,
                'message': f'New location "{new_location_name}" with description "{description}" and location type index "{location_type_index}" created successfully under parent location ID {parent_location_id}.'
            }
        else:
            return {
                'simulation': False,
                'message': f'Failed to create new location. Status code: {response.status_code}',
                'details': response.json()
            }


@app.route('/')
def index():
    # Get all locations
    locations = get_all_locations()

    # Find the highest progressive number
    #highest_number = find_highest_progressive_number(locations)

    # Calculate the next available progressive number
    #next_number = highest_number + 1

    if request.method == 'POST':


        return render_template  ('index.html', locations=locations)
    
    return render_template('index.html', locations=locations)

@app.route('/create_locations', methods=['POST'])
def create_locations():
    num_new_locations = int(request.form['num_new_locations'])
    parent_location_name = request.form['parent_location_name']
    simulate = request.form['simulate'].lower() == 'true'

    # Get all locations
    locations = get_all_locations()

    # Find the highest progressive number
    highest_number = find_highest_progressive_number(locations)

    # Get the parent location ID by name
    parent_location_id = get_location_id_by_name(parent_location_name)

    if parent_location_id:
        results = []
        # Create the specified number of new locations
        for i in range(1, num_new_locations + 1):
            result = create_new_location(highest_number + i, parent_location_id, simulate)
            results.append(result)
        
        # Render the results in an HTML page
        results_html = '''
        <html>
        <head>
            <link rel="stylesheet" type="text/css" href="/static/styles.css">
        </head>
        <body>
            <img src="/static/logo.png" alt="Logo" style="width:100px;height:auto;">
            <h2>Operation Results</h2>
            <ul>
            {% for result in results %}
                <li>{{ result.message }}</li>
            {% endfor %}
            </ul>
            <a href="/">Go back</a>
        </body>
        </html>
        '''
        return render_template_string(results_html, results=results)
    else:
        return jsonify({'error': f'Parent location "{parent_location_name}" not found.'}), 404

@app.route('/get_location_names', methods=['GET'])
def get_location_names():
    locations = get_all_locations()
    location_data = [{'name': location['name'], 'path': location['pathstring']} for location in locations]
    return jsonify(location_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5556)