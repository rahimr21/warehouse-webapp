# Tech Recycling Warehouse Management System

A simple web application for managing tech recycling boxes and containers in a warehouse environment.

## Features

- Box Management (create, view, edit, delete)
- Container Management with box assignment
- Product tracking and reporting
- Export functionality for container reports

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

Note: If you encounter SQLAlchemy compatibility issues with Python 3.13, the requirements.txt has been updated with compatible versions.

4. Initialize the database:
```bash
flask init-db
```

5. Run the application:
```bash
flask run --host=0.0.0.0
```

The application will be available at `http://localhost:5000` on the host machine and `http://<host-ip>:5000` on other devices in the LAN.

## Usage

1. Create boxes by entering box numbers, weights, and contents
2. View and manage boxes in the boxes list
3. Create containers and assign boxes to them
4. Generate container reports for shipping documentation

## Note

This application is designed for local network use only. No authentication is implemented as it's meant for internal warehouse use. 