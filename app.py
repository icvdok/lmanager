from flask import Flask
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Import and register blueprints
from routes.home import home_bp
from routes.slcreate import slcreate_bp
from routes.slmove import slmove_bp
from routes.backup import backup_bp

app.register_blueprint(home_bp)
app.register_blueprint(slcreate_bp)
app.register_blueprint(slmove_bp)
app.register_blueprint(backup_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5556, debug=True)
