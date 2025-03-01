from flask import Blueprint, render_template, request
import logging
from utils.utils import get_all_locations, get_sublocations, move_sublocations, get_inventree_version
import os

slmove_bp = Blueprint('slmove', __name__)

@slmove_bp.route('/slmove', methods=['GET', 'POST'])
def slmove():
    base_url = os.getenv('BASE_URL')
    version_info = get_inventree_version()
    version = version_info.get('server', 'Unknown version')
    
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

    return render_template('slmove.html', base_url=base_url, version=version, locations=locations, sublocations=sublocations, source_location_parent=source_location_parent, target_location_parent=target_location_parent)
