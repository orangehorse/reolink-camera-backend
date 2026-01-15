# Reolink Camera Control Backend

Flask API for controlling Reolink cameras via Reolink Cloud API.

## Features

- Flask REST API for camera control
- Reolink Cloud integration
- User authentication with fixed credentials
- Support for PTZ (Pan-Tilt-Zoom) camera control
- CORS enabled for frontend access

## Requirements

- Python 3.11+
- Flask
- Requests library
- Python-dotenv

## Installation
```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:
