#!/bin/bash

sudo apt-get update

# Uninstall old system python version
sudo apt-get remove python
sudo apt autoremove

# Install python3
sudo apt-get install python3

# Create virtual environment
python3 -m venv venv

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt
