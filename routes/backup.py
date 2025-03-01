from flask import Blueprint, render_template, request
import logging
from utils.utils import backup_inventree, get_inventree_version
import os

backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/backup', methods=['GET', 'POST'])
def backup():
    base_url = os.getenv('BASE_URL')
    version_info = get_inventree_version()
    version = version_info.get('server', 'Unknown version')
    
    if request.method == 'POST':
        message = "Backup in progress..."
        try:
            backup_inventree()
            message = "Backup successful."
        except Exception as e:
            message = f"Backup failed: {str(e)}"
        return render_template('backup.html', base_url=base_url, version=version, message=message)
    return render_template('backup.html', base_url=base_url, version=version)
