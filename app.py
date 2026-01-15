import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
REOLINK_EMAIL = os.getenv('REOLINK_EMAIL')
REOLINK_PASSWORD = os.getenv('REOLINK_PASSWORD')
CAMERA_UID = os.getenv('CAMERA_UID')

# Fixed website credentials
WEBSITE_ID = '860'
WEBSITE_PASSWORD = 'ocean'

# Reolink Cloud API endpoints
REOLINK_API_BASE = 'https://api.reolink.com/v1'

# In-memory token storage (for demo purposes)
valid_tokens = set()


class ReonlinkCloudAPI:
    """Handle Reolink Cloud API interactions"""
    
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.token_expiration = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Reolink Cloud"""
        try:
            url = f"{REOLINK_API_BASE}/login"
            payload = {
                "email": self.email,
                "password": self.password
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 0:
                self.access_token = data['data']['access_token']
                self.refresh_token = data['data']['refresh_token']
                self.token_expiration = datetime.now() + timedelta(hours=23)
                return True
            else:
                print(f"Authentication failed: {data.get('msg')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Authentication error: {e}")
            return False
    
    def get_camera_status(self, camera_uid):
        """Get camera status from Reolink Cloud"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {'Authorization': f'Bearer {self.access_token}'}
            url = f"{REOLINK_API_BASE}/camera/{camera_uid}"
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 0:
                camera_data = data['data']
                return {
                    'status': 'Online' if camera_data.get('status') == 1 else 'Offline',
                    'name': camera_data.get('name'),
                    'uid': camera_data.get('uid'),
                    'pan': 0,
                    'tilt': 0,
                    'zoom': 1
                }
            else:
                return {'error': data.get('msg')}
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
    
    def ptz_control(self, camera_uid, direction, value):
        """Control camera PTZ (Pan-Tilt-Zoom)"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {'Authorization': f'Bearer {self.access_token}'}
            url = f"{REOLINK_API_BASE}/camera/{camera_uid}/ptz"
            
            payload = {
                direction: value
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 0:
                return {'success': True, 'message': f'{direction} command sent'}
            else:
                return {'success': False, 'error': data.get('msg')}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': str(e)}
    
    def recall_preset(self, camera_uid, preset_id):
        """Recall a saved camera preset"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {'Authorization': f'Bearer {self.access_token}'}
            url = f"{REOLINK_API_BASE}/camera/{camera_uid}/preset/{preset_id}"
            
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 0:
                return {'success': True, 'message': 'Preset recalled'}
            else:
                return {'success': False, 'error': data.get('msg')}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': str(e)}
    
    def get_presets(self, camera_uid):
        """Get list of camera presets"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {'Authorization': f'Bearer {self.access_token}'}
            url = f"{REOLINK_API_BASE}/camera/{camera_uid}/presets"
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 0:
                presets = data['data'].get('presets', [])
                return presets
            else:
                return []
        except requests.exceptions.RequestException as e:
            print(f"Get presets error: {e}")
            return []


def generate_token(user_id):
    """Generate JWT token for website users"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    valid_tokens.add(token)
    return token


def verify_token(token):
    """Verify JWT token"""
    try:
        if token not in valid_tokens:
            return False
        jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return True
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False


def token_required(f):
    """Decorator to require valid token"""
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'No token provided'}), 401
        
        try:
            token = token.split(' ')[1]
            if not verify_token(token):
                return jsonify({'success': False, 'message': 'Invalid token'}), 401
        except IndexError:
            return jsonify({'success': False, 'message': 'Invalid token format'}), 401
        
        return f(*args, **kwargs)
    
    decorated.__name__ = f.__name__
    return decorated


# Initialize Reolink API client
reolink_api = None

try:
    if REOLINK_EMAIL and REOLINK_PASSWORD and CAMERA_UID:
        reolink_api = ReonlinkCloudAPI(REOLINK_EMAIL, REOLINK_PASSWORD)
except Exception as e:
    print(f"Failed to initialize Reolink API: {e}")


# Routes

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint - uses fixed credentials"""
    data = request.get_json()
    
    user_id = data.get('id')
    password = data.get('password')
