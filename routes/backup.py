from flask import Blueprint, render_template, request
import logging
from utils.utils import backup_inventree

backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/backup', methods=['GET', 'POST'])
def backup():
    if request.method == 'POST':
        message = "Backup in progress..."
        try:
            backup_inventree()
            message = "Backup successful."
        except Exception as e:
            message = f"Backup failed: {str(e)}"
        return render_template('backup.html', message=message)
    return render_template('backup.html')
