#!/bin/bash
# Startup script for Voter List OCR Web Application

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Start the Flask application
python app.py

