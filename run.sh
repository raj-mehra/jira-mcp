#!/bin/bash

# Check if virtual environment exists, if not run setup
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    ./setup.sh
fi

# Activate virtual environment and run the app with Python
source venv/bin/activate && python main.py "$@" 