from flask import Blueprint, render_template, request, redirect, url_for
import logging
from utils.utils import get_all_locations, get_location_types, find_highest_progressive_number, generate_new_locations, create_new_locations

slcreate_bp = Blueprint('slcreate', __name__)

@slcreate_bp.route('/slcreate', methods=['GET', 'POST'])
def slcreate():
    locations = get_all_locations()
    logging.debug('r_Locations function executed')
    
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

            highest_number, matching_locations = find_highest_progressive_number(locations, location_types, selected_type)
            logging.debug(f'r_Highest number identified: {highest_number}')
            logging.debug(f'r_Matching locations identified: {matching_locations}')
            
            next_number = highest_number + 1
            logging.debug(f'r_Next number is: {next_number}')
            
            new_locations = generate_new_locations(matching_locations, num_new_locations, highest_number, selected_type)
            logging.debug(f'r_New locations to create: {new_locations}')
            
            all_locations = matching_locations + new_locations
            all_locations.sort(key=lambda x: int(x.split('_')[1]))
            
            return render_template('slcreate.html', locations=locations, highest_number=highest_number, next_number=next_number, location_types=location_types, all_locations=all_locations, new_locations=new_locations, parent_location_name=parent_location_name, selected_type=selected_type, num_new_locations=num_new_locations)
        
        elif 'execute_creation' in request.form:
            logging.debug(f'r_execute_click')
            new_locations = request.form.getlist('new_locations')
            parent_location_name = request.form.get('parent_location_name')
            selected_type = request.form.get('location_type')
            create_new_locations(locations, new_locations, parent_location_name, selected_type, location_types)
            return redirect(url_for('slcreate.slcreate'))

    return render_template('slcreate.html', locations=locations, highest_number=0, next_number=1, location_types=location_types, all_locations=[], new_locations=[], parent_location_name='', selected_type='', num_new_locations=1)
