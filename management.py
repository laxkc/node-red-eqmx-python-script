from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String
from datetime import datetime
import paho.mqtt.client as mqtt
import threading
import json # For parsing JSON data


# Create the Flask application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress warnings
db = SQLAlchemy(app)

# Create a User model
class User(db.Model):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default='Guest')
    email = Column(String, default='guest@guest.com')
    password = Column(String, default='demo123')
    mobile = Column(String, default='123456789')
    address = Column(String, default='15 Demo Street')
    college_name = Column(String, default='Cambrian')

# Create a Device model
class Device(db.Model):
    __tablename__ = 'device'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cpu = db.Column(db.String, nullable=False)
    memory = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# MQTT Setup
mqtt_broker = "broker.emqx.io"  # Public MQTT broker
mqtt_port = 1883
mqtt_topic = "IOTDATA"

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code: {rc}")
    client.subscribe(mqtt_topic)

def on_message(client, userdata, msg):
    print(f"Message received on topic {msg.topic}: {msg.payload}")
    data = msg.payload.decode("utf-8")
    
    # Try to handle JSON data
    try:
        json_data = json.loads(data)
        print("Parsed JSON:", json_data)
        if isinstance(json_data, dict) and "cpu" in json_data and "memory" in json_data:
            cpu = json_data["cpu"]
            memory = json_data["memory"]
        else:
            # If cpu or memory is missing in the JSON, set them to "Unknown"
            print("Missing 'cpu' or 'memory' in JSON, setting to 'Unknown'")
            cpu = "Unknown"
            memory = "Unknown"
    except json.JSONDecodeError:
        # If it's not JSON, fallback to splitting the string
        print("Data is not valid JSON, splitting string")
        if ',' in data:
            cpu, memory = data.split(",", 1)
        else:
            cpu = data
            memory = "Unknown"

    print(f"Extracted cpu: {cpu}, memory: {memory}")
    
    # Create a new device object
    device = Device(cpu=cpu, memory=memory)

    # Ensure the operation happens within an application context
    with app.app_context():
        db.session.add(device)
        db.session.commit()


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqtt_broker, mqtt_port, 60)

# Start MQTT client in a separate thread
mqtt_thread = threading.Thread(target=client.loop_forever)
mqtt_thread.start()

# Create the tables within the application context
with app.app_context():
    db.create_all()

# Routes for the User Management System
@app.route('/')
def home():
    return 'Welcome to User Management System'

# Add a new user to the database
@app.route('/add_user', methods=['POST'])
def add_user():
    try:
        data = request.get_json()
        new_user = User(
            name=data.get('name', 'Guest'),
            email=data.get('email', 'guest@guest.com'),
            password=data.get('password', 'demo123'),
            mobile=data.get('mobile', '123456789'),
            address=data.get('address', '15 Demo Street'),
            college_name=data.get('college_name', 'Cambrian')
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 400

# Retrieve a user from the database
@app.route('/edit_user', methods=['PUT'])
def edit_user():
    try:
        data = request.get_json()
        user = User.query.filter_by(id=data['id']).first()
        if user:
            user.name = data.get('name', user.name)
            user.email = data.get('email', user.email)
            user.password = data.get('password', user.password)
            user.mobile = data.get('mobile', user.mobile)
            user.address = data.get('address', user.address)
            user.college_name = data.get('college_name', user.college_name)
            db.session.commit()
            return jsonify({'message': 'User updated successfully'}), 200
        else:
            return jsonify({'message': 'User not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 400

# Update a user in the database
@app.route('/update_user', methods=['PUT'])
def update_user():
    try:
        data = request.get_json()
        user = User.query.filter_by(id=data['id']).first()
        if user:
            user.mobile = data.get('mobile', user.mobile)
            user.address = data.get('address', user.address)
            db.session.commit()
            return jsonify({'message': 'User updated successfully'}), 200
        else:
            return jsonify({'message': 'User not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 400

# Delete a user from the database
@app.route('/delete_user', methods=['DELETE'])
def delete_user():
    try:
        data = request.get_json()
        user = User.query.filter_by(id=data['id']).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            return jsonify({'message': 'User deleted successfully'}), 200
        else:
            return jsonify({'message': 'User not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 400

# Retrieve all users from the database
@app.route('/get_all_users', methods=['GET'])
def get_all_users():
    try:
        users = User.query.all()  # Fetch all users from the database
        user_list = []
        for user in users:
            user_data = {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'password': user.password,
                'mobile': user.mobile,
                'address': user.address,
                'college_name': user.college_name
            }
            user_list.append(user_data)
        return jsonify({'users': user_list}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400


@app.route('/add_device', methods=['POST'])
def add_device():
    data = request.get_json()
    new_device = Device(
        cpu=data.get('cpu'),
        memory=data.get('memory'),
    )
    db.session.add(new_device)
    db.session.commit()
    return jsonify({'message': 'Device added successfully'}), 201

@app.route('/get_all_devices', methods=['GET'])
def get_all_devices():
    devices = Device.query.all()
    device_list = [{'id': device.id, 'cpu': device.cpu, 'memory': device.memory, 'timestamp': device.timestamp} 
                   for device in devices]
    return jsonify({'devices': device_list}), 200

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
