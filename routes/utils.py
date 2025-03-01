import requests
import logging
import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

api_token = os.getenv('INVENTREE_API_TOKEN')
base_url = os.getenv('BASE_URL')
ssh_host = os.getenv('SSH_HOST')
ssh_user = os.getenv('SSH_USER')
ssh_key_path = os.getenv('SSH_KEY_PATH')
docker_compose_path = os.getenv('DOCKER_COMPOSE_PATH')

headers = {
    'Authorization': f'Token {api_token}',
    'Content-Type': 'application/json'
}

def get_all_locations():
    logging.debug('f_call function get_all_location')
    url = f'{base_url}stock/location/'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def get_sublocations(parent_id):
    logging.debug('f_call function get_sublocations')
    url = f'{base_url}stock/location/'
    response = requests.get(url, headers=headers, params={'parent': parent_id})
    if response.status_code == 200:
        return response.json()
    return []

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

    prefix_map = {
        1: 'a_',  # Shelf
        2: 'b_',  # Box
        3: 's_',  # Sorter
        4: 'g_'   # Bin
    }

    prefix = prefix_map.get(int(selected_type))
    if not prefix:
        logging.error(f'f_No prefix found for selected type: {selected_type}')
        return 0, []

    logging.debug(f'f_Prefix: {prefix}')

    matching_locations = [loc['name'] for loc in locations if loc['name'].startswith(prefix)]
    logging.debug(f'f_Matching locations: {matching_locations}')

    valid_locations = []
    for loc in matching_locations:
        try:
            int(loc[len(prefix):])
            valid_locations.append(loc)
        except ValueError:
            logging.warning(f'f_Invalid number format in location name: {loc}')

    logging.debug(f'f_Valid locations: {valid_locations}')

    valid_locations.sort(key=lambda x: int(x[len(prefix):]))

    highest_number = max([int(loc[len(prefix):]) for loc in valid_locations], default=0)
    logging.debug(f'f_Highest number: {highest_number}')

    return highest_number, valid_locations

def generate_new_locations(matching_locations, num_new_locations, highest_number, selected_type):
    logging.debug('f_call function generate_new_locations')
    new_locations = []

    prefix_map = {
        1: 'a_',  # Shelf
        2: 'b_',  # Box
        3: 's_',  # Sorter
        4: 'g_'   # Bin
    }

    prefix = prefix_map.get(int(selected_type))
    if not prefix:
        logging.error(f'f_No prefix found for selected type: {selected_type}')
        return new_locations

    existing_numbers = [int(loc.split('_')[1]) for loc in matching_locations]
    
    all_numbers = set(range(1, highest_number + num_new_locations + 1))
    unused_numbers = sorted(all_numbers - set(existing_numbers))
    
    for i in range(min(num_new_locations, len(unused_numbers))):
        new_locations.append(f'{prefix}{unused_numbers[i]:04d}')
    
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
        return location_types
    else:
        return {
            'message': f'Failed to retrieve location types. Status code: {response.status_code}',
            'details': response.json()
        }

def create_new_locations(locations, new_locations, parent_location_name, selected_type, location_types):
    logging.debug('f_call function create_new_locations')
    description_rules = {
        'g_': 'gridfinity bin',
        's_': 'sorter organizer',
        'b_': 'box contenitore',
        'a_': 'shelf armadio'
    }

    if not selected_type:
        logging.error('f_Selected type is empty')
        return

    type_name = None
    for location_type in location_types:
        if location_type['pk'] == int(selected_type):
            type_name = location_type['name']
            break

    if type_name is None:
        logging.error(f'f_Invalid selected type: {selected_type}')
        return

    description = description_rules.get(type_name, '')

    parent_location_id = next((loc['pk'] for loc in locations if loc['pathstring'] == parent_location_name), None)
    if parent_location_id is None:
        logging.error(f'f_No location found with name: {parent_location_name}')
        return

    for location in new_locations:
        data = {
            'name': location,
            'description': description,
            'parent': parent_location_id,
            'location_type': int(selected_type)
        }

        logging.info(f'f_Would create location: {data}')
        # Uncomment the following lines to enable actual creation
        # response = requests.post(f'{base_url}stock/location/', headers=headers, json=data)
        # if response.status_code == 201:
        #     logging.info(f'Successfully created location: {location}')
        # else:
        #     logging.error(f'Failed to create location: {location}, response: {response.text}')

def backup_inventree():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.debug(f'Connecting to {ssh_host} as {ssh_user} using key {ssh_key_path}')
        ssh.connect(ssh_host, username=ssh_user, key_filename=ssh_key_path)

        command = f'cd {docker_compose_path} && docker compose -f docker-compose.yml run inventree-server invoke backup'
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            logging.info(f'Backup successful: {stdout.read().decode()}')
        else:
            logging.error(f'Backup failed: {stderr.read().decode()}')
            exit(1)
        ssh.close()
    except Exception as e:
        logging.error(f'Backup failed: {str(e)}')
        exit(1)
