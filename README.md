# BEEMO 2.0 CODES
This repository contains the codes used for the project and includes the following:
1. Web Application
   - Predictors
   - Audio Analysis
3. Sensor System
   - Camera
   - Temperature and Humidity Sensor

# Project Overview
BeemoDos is a Django-based web application designed to analyze bee audio recordings, generate spectrograms, and provide insights into bee behavior using machine learning.

Key Components include:
1. Audio recording functionality
2. Spectrogram generation
3. Machine learning model inference for bee behavior detection
4. Automated hourly audio analysis
5. Prerequisites
6. Python 3.9+
7. pip
8. virtualenv (recommended)
9. Git
10. FFmpeg (for audio processing)

Take note of the following for Logging:
- Logs are managed by Django's logging system
- Check Django log files for detailed analysis results
- Logs include recording configuration, device info, and analysis outcomes
- Machine Learning Models
- Pre-trained models are excluded from the repository
- Place your machine learning models in the training_models/ directory
- Supported model formats: .keras, .h5, .pkl
- Development Workflow
- Always work in a virtual environment
- Install new dependencies with pip install and update requirements.txt
- Run tests before committing: python manage.py test

# Install Dependencies
for installation dependencies, refer to "requirements.txt"

Type:
*pip install -r requirements.txt*

# Server Run
refer to "manage.py"
