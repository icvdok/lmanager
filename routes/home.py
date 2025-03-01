from flask import Blueprint, render_template
from utils.utils import get_inventree_version
import os

home_bp = Blueprint('home', __name__)

@home_bp.route('/', methods=['GET'])
def index():
    base_url = os.getenv('BASE_URL')
    version_info = get_inventree_version()
    version = version_info.get('server', 'Unknown version')
    return render_template('home.html', base_url=base_url, version=version)
