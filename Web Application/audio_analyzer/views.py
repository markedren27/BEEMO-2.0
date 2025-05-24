import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend before importing pyplot

import os
import logging
import numpy as np
import sounddevice as sd
import librosa
import matplotlib.pyplot as plt
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from scipy.io import wavfile
import json
import soundfile as sf
import re
import traceback
import requests
import time
from datetime import datetime, timedelta  # Added timedelta for good measure

import tensorflow as tf

import sys
sys.path.append(os.path.join(settings.BASE_DIR, 'predictors'))
import BNBpredictor
import QNQpredictor
import TOOTpredictor

# Import Discord utilities
from .discord_utils import send_discord_message

# Import Blynk utilities
from .blynk_utils import blynk_connection

# Import Google Sheets utility
from .sheets_utils import save_frequency_to_sheets

logger = logging.getLogger(__name__)

def index(request):
    """
    Render the main index page for bee audio analysis
    """
    # Get list of available audio input devices
    devices = sd.query_devices()
    input_devices = [
        {
            'index': i, 
            'name': device['name'], 
            'max_input_channels': device['max_input_channels']
        } 
        for i, device in enumerate(devices) 
        if device['max_input_channels'] > 0
    ]
    
    return render(request, 'index.html', {
        'input_devices': input_devices
    })

@csrf_exempt
def record_audio(request):
    """
    Handle audio recording request with device selection
    """
    try:
        # Get device and recording parameters from request
        device_index = int(request.POST.get('device', 0))
        duration = float(request.POST.get('duration', 5))  # seconds
        sample_rate = int(request.POST.get('sample_rate', 44100))  # Hz
        
        # Record audio from specified device
        recording = sd.rec(
            int(duration * sample_rate), 
            samplerate=sample_rate, 
            channels=1, 
            dtype='float64',
            device=device_index
        )
        sd.wait()
        
        # Save recording
        audio_filename = 'bee_recording.wav'
        audio_path = os.path.join(settings.MEDIA_ROOT, audio_filename)
        
        # Ensure media directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        
        # Write audio file using scipy
        wavfile.write(audio_path, sample_rate, (recording * 32767).astype(np.int16))
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Audio recorded successfully',
            'filename': audio_filename,
            'device': device_index
        })
    
    except Exception as e:
        logger.error(f"Audio recording error: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)

def get_audio_devices(request):
    """
    List available audio input devices
    """
    try:
        import sounddevice as sd
        
        # Get the list of all devices
        all_devices = sd.query_devices()
        
        # Get the list of input devices
        input_devices = [
            {
                'index': i, 
                'name': device['name'], 
                'max_input_channels': device['max_input_channels']
            } 
            for i, device in enumerate(all_devices) 
            if device['max_input_channels'] > 0
        ]
        
        # Log input devices for debugging
        logger.info(f"Input devices found: {input_devices}")
        
        return JsonResponse({
            'status': 'success', 
            'devices': input_devices
        })
    except ImportError as e:
        logger.error(f"Failed to import sounddevice: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': f'Sounddevice import failed: {str(e)}'
        }, status=500)
    except Exception as e:
        import traceback
        logger.error(f"Error listing audio devices: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)

def generate_spectrogram(request=None, audio_path=None, predictor_type='BNQ'):
    """
    Generate spectrogram from audio file
    
    Args:
        request (HttpRequest, optional): Django request object
        audio_path (str, optional): Path to the input audio file
        predictor_type (str, optional): Type of predictor for naming, defaults to 'BNQ'
    
    Returns:
        JsonResponse or str path to spectrogram
    """
    try:
        # Ensure media directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        
        # If called from URL route, find the most recent audio file
        if request is not None:
            # Find the most recent audio file
            audio_files = [f for f in os.listdir(settings.MEDIA_ROOT) if f.startswith('bee_recording')]
            if not audio_files:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No audio file found'
                }, status=404)
            
            # Use the most recent audio file
            audio_path = os.path.join(settings.MEDIA_ROOT, max(audio_files, key=lambda f: os.path.getctime(os.path.join(settings.MEDIA_ROOT, f))))
        
        # Validate audio path
        if audio_path is None or not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return JsonResponse({
                'status': 'error',
                'message': 'Audio file not found'
            }, status=404)
        
        # Generate timestamp for unique filename
        timestamp = ""
        
        # Create spectrogram filename with predictor type
        spectrogram_filename = f'BeemoDosSpectrogram_{predictor_type}_{timestamp}.png'
        spectrogram_path = os.path.join(settings.MEDIA_ROOT, spectrogram_filename)
        
        # Load audio file
        y, sr = librosa.load(audio_path)
        
        # Create spectrogram
        plt.figure(figsize=(12, 8))
        librosa.display.specshow(
            librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max), 
            sr=sr, 
            x_axis='time', 
            y_axis='hz'
        )
        plt.colorbar(format='%+2.0f dB')
        plt.title(f'Spectrogram - {predictor_type}')
        plt.tight_layout()
        
        # Save spectrogram
        plt.savefig(spectrogram_path)
        plt.close()
        
        # If called from URL route, return JSON response
        if request is not None:
            return JsonResponse({
                'status': 'success',
                'spectrogram_path': spectrogram_filename
            })
        
        # If called programmatically, return spectrogram path
        return spectrogram_path
    
    except Exception as e:
        logger.error(f"Spectrogram generation error for {predictor_type}: {e}")
        
        # If called from URL route, return error JSON
        if request is not None:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
        
        # If called programmatically, return None
        return None

@csrf_exempt
def record_and_generate_spectrograms(request):
    """
    Record audio for multiple predictors and generate spectrograms
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        duration = data.get('duration', 5)  # Default 5 seconds
        device_index = data.get('device_index', None)

        # Validate inputs
        if not isinstance(duration, (int, float)) or duration <= 0:
            return JsonResponse({
                'status': 'error', 
                'message': 'Invalid recording duration'
            }, status=400)

        # Predictors to record
        predictors = ['BNQ', 'QNQ', 'TOOT']
        num_recordings = 1

        # Prepare storage for recordings and spectrograms
        all_recordings = {}
        all_spectrograms = {}
        analysis_results = {}

        # Create directory for this recording session
        session_timestamp = ""
        recordings_base_dir = os.path.join(settings.MEDIA_ROOT, 'recordings')
        session_dir = os.path.join(recordings_base_dir, session_timestamp)
        os.makedirs(session_dir, exist_ok=True)

        # Ensure proper permissions
        os.chmod(session_dir, 0o755)

        # Detailed logging of paths
        print("Path Configuration:")
        print(f"BASE_DIR: {settings.BASE_DIR}")
        print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        print(f"MEDIA_URL: {settings.MEDIA_URL}")
        print(f"Session Directory: {session_dir}")
        print(f"Recordings Base Directory: {recordings_base_dir}")

        # Find the most recent recording directory
        try:
            # List all subdirectories in the recordings directory
            existing_sessions = [
                d for d in os.listdir(recordings_base_dir) 
                if os.path.isdir(os.path.join(recordings_base_dir, d))
            ]
            
            # Sort sessions by timestamp (newest first)
            existing_sessions.sort(reverse=True)
            
            print("Existing Recording Sessions:", existing_sessions)
        except Exception as dir_list_error:
            print(f"Error listing recording sessions: {dir_list_error}")
            existing_sessions = []

        # Record and process for each predictor
        for predictor in predictors:
            predictor_recordings = []
            predictor_spectrograms = []

            for i in range(num_recordings):
                # Generate unique filenames
                audio_filename = f'{predictor}_recording_{i+1}.wav'
                spectrogram_filename = f'{predictor}_spectrogram_{i+1}.png'
                
                # Full paths with absolute resolution
                audio_path = os.path.abspath(os.path.join(session_dir, audio_filename))
                spectrogram_path = os.path.abspath(os.path.join(session_dir, spectrogram_filename))

                # Record audio
                sample_rate = 44100
                recording = sd.rec(
                    int(duration * sample_rate), 
                    samplerate=sample_rate, 
                    channels=1, 
                    dtype='float64',
                    device=device_index
                )
                sd.wait()  # Wait for recording to complete

                # Save audio file
                sf.write(audio_path, recording, sample_rate)
                os.chmod(audio_path, 0o644)

                # Generate spectrogram
                plt.figure(figsize=(10, 4))
                librosa.display.specshow(
                    librosa.amplitude_to_db(
                        np.abs(librosa.stft(recording.flatten())), 
                        ref=np.max
                    ), 
                    sr=sample_rate, 
                    x_axis='time', 
                    y_axis='hz'
                )
                plt.colorbar(format='%+2.0f dB')
                plt.title(f'{predictor} Spectrogram')
                plt.tight_layout()
                plt.savefig(spectrogram_path)
                os.chmod(spectrogram_path, 0o644)
                plt.close()

                # Relative paths for frontend
                rel_audio_path = os.path.relpath(audio_path, settings.MEDIA_ROOT)
                rel_spectrogram_path = os.path.relpath(spectrogram_path, settings.MEDIA_ROOT)

                # Detailed path logging
                print(f"\nSpectrogram for {predictor}:")
                print(f"  Full Path: {spectrogram_path}")
                print(f"  Relative Path: {rel_spectrogram_path}")
                print(f"  Media URL Path: {settings.MEDIA_URL}{rel_spectrogram_path}")
                print(f"  File Exists: {os.path.exists(spectrogram_path)}")

                # Store recordings and spectrograms
                predictor_recordings.append({
                    'audio_path': rel_audio_path,
                    'spectrogram_path': rel_spectrogram_path
                })
                
                # Use full media URL
                predictor_spectrograms.append(f'{settings.MEDIA_URL}{rel_spectrogram_path}')

            # Store for each predictor
            all_recordings[predictor] = predictor_recordings
            all_spectrograms[predictor] = predictor_spectrograms

        # Collect all spectrogram paths for analysis
        all_spectrogram_paths = []
        for predictor, paths in all_spectrograms.items():
            # Convert from media URL to relative path
            for path in paths:
                rel_path = path.replace(settings.MEDIA_URL, '')
                all_spectrogram_paths.append(rel_path)
        
        # Initialize analysis_results with default values
        analysis_results = {
            'BNQ': {'predicted_class': 0, 'confidence': 0.0, 'label': 'No Analysis', 'f1_score': 0.0, 'precision': 0.0, 'raw_result': [0, 0, 0, 0]},
            'QNQ': {'predicted_class': 0, 'confidence': 0.0, 'label': 'No Analysis', 'f1_score': 0.0, 'precision': 0.0, 'raw_result': [0, 0, 0, 0]},
            'TOOT': {'predicted_class': 0, 'confidence': 0.0, 'label': 'No Analysis', 'f1_score': 0.0, 'precision': 0.0, 'raw_result': [0, 0, 0, 0]}
        }
        
        # Analyze the spectrograms and send Discord notification
        if all_spectrogram_paths:
            logger.info(f"Calling analyze_audio with {len(all_spectrogram_paths)} spectrograms")
            
            # Create a mock request with the spectrogram paths in the body
            class MockRequest:
                method = 'POST'
                body = json.dumps({'spectrograms': all_spectrogram_paths}).encode('utf-8')
            
            # Call analyze_audio
            try:
                logger.info(f"About to call analyze_audio with paths: {all_spectrogram_paths}")
                analysis_response = analyze_audio(MockRequest())
                logger.info(f"analyze_audio response status: {analysis_response.status_code}")
                
                # Debug the response content
                response_content = analysis_response.content.decode('utf-8')
                logger.info(f"Raw response content: {response_content}")
                
                analysis_data = json.loads(response_content)
                analysis_results = analysis_data.get('analysis_results', {})
                
                logger.info(f"Analysis completed: {json.dumps(analysis_results, indent=2)}")
            except Exception as analysis_error:
                logger.error(f"Error in analysis: {analysis_error}")
                logger.error(traceback.format_exc())
        else:
            logger.warning("No spectrograms available for analysis")

        # Return successful response
        return JsonResponse({
            'status': 'success',
            'recordings': all_recordings,
            'spectrograms': all_spectrograms,
            'analysis_results': analysis_results,
            'debug_info': {
                'existing_sessions': existing_sessions,
                'current_session': session_timestamp
            }
        })

    except Exception as e:
        # Log the full error
        logger.error(f"Error in record_and_generate_spectrograms: {str(e)}")
        logger.error(traceback.format_exc())

        # Return error response
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)

def predictors_view(request):
    """
    Render the predictors analysis page
    """
    return render(request, 'predictors.html')

@csrf_exempt
def analyze_audio(request):
    try:
        # Ensure Django settings are imported at the top of the function
        from django.conf import settings

        if request.method != 'POST':
            return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

        # Parse request data
        data = json.loads(request.body)
        spectrograms = data.get('spectrograms', [])

        # Validate input
        if not spectrograms:
            return JsonResponse({'error': 'No spectrograms provided'}, status=400)

        # Perform analysis for each predictor
        analysis_results = {}

        # Predictor configurations with more robust error handling
        predictors = [
            {
                'name': 'BNQ',
                'function': BNBpredictor.predict_and_display,
                'labels': ['No Bees Detected', 'Bees Detected']
            },
            {
                'name': 'QNQ',
                'function': QNQpredictor.QNQpredictor,
                'labels': ['No Queen Detected', 'Queen Detected']
            },
            {
                'name': 'TOOT',
                'function': TOOTpredictor.predict_and_display,
                'labels': ['No Tooting', 'Tooting']
            }
        ]

        # Process each predictor
        for predictor in predictors:
            try:
                # Convert relative path to absolute path if needed
                spectrogram_path = spectrograms[0]
                if not os.path.isabs(spectrogram_path):
                    spectrogram_path = os.path.join(settings.MEDIA_ROOT, spectrogram_path)
                
                # Ensure the file exists before prediction
                if not os.path.exists(spectrogram_path):
                    logger.error(f"Spectrogram file not found: {spectrogram_path}")
                    raise FileNotFoundError(f"Spectrogram file not found: {spectrogram_path}")
                
                logger.info(f"Predicting {predictor['name']} using file: {spectrogram_path}")
                result = predictor['function'](spectrogram_path)
                
                # Log raw result for debugging
                logger.info(f"{predictor['name']} Raw Result: {result}")
                
                # Safely extract prediction details with extensive error checking
                if not isinstance(result, (list, tuple)) or len(result) < 2:
                    logger.error(f"{predictor['name']} returned invalid result: {result}")
                    raise ValueError(f"Invalid prediction result for {predictor['name']}")
                
                # Handle different return formats (4 or 2 elements)
                if len(result) == 4:
                    predicted_class, confidence, f1, precision = result
                else:
                    predicted_class, confidence = result
                    f1, precision = 0.0, 0.0
                
                # Log detailed prediction information
                logger.info(f"{predictor['name']} Prediction - Class: {predicted_class}, Raw Confidence: {confidence}")
                
                # Store results with explicit type conversion
                analysis_results[predictor['name']] = {
                    'predicted_class': int(predicted_class),
                    'confidence': float(confidence) * 100,  # Multiply by 100 for frontend display
                    'label': predictor['labels'][int(predicted_class)],
                    'f1_score': float(f1),
                    'precision': float(precision),
                    'raw_result': list(result)  # Ensure full result is preserved
                }
            except Exception as e:
                logger.error(f"{predictor['name']} prediction error: {e}")
                analysis_results[predictor['name']] = {
                    'predicted_class': 0,
                    'confidence': 0.0,  # Keep as 0.0 for failed predictions
                    'label': 'Prediction Failed',
                    'error': str(e)
                }

        # Trigger Blynk event with analysis results
        try:
            # Convert analysis results to native types to ensure JSON serializability
            def convert_numpy_to_native(obj):
                """
                Recursively convert numpy types to native Python types
                """
                if isinstance(obj, np.float32):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {k: convert_numpy_to_native(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_to_native(v) for v in obj]
                return obj

            safe_analysis_results = convert_numpy_to_native(analysis_results)

            # Predefined action messages matching audio_recorder.js
            action_messages = {
                'BNQ': {
                    'positive': 'Hive Activity Confirmed. Continue regular monitoring.',
                    'negative': 'No buzzing detected. Inspect the hive for potential issues.'
                },
                'QNQ': {
                    'positive': 'Queen Bee Presence Confirmed. Hive appears stable.',
                    'negative': 'Queen Bee Might Be Absent. Prepare to introduce a new queen if necessary.'
                },
                'TOOT': {
                    'positive': 'Queen Tooting Detected. Potential queen emergence or competition.',
                    'negative': 'No queen tooting detected. Continue monitoring.'
                }
            }

            # Prepare results for Blynk with predefined messages
            def get_blynk_result(predictor_key):
                predictor_result = safe_analysis_results.get(predictor_key, {})
                confidence = predictor_result.get('confidence', 0)
                
                # Determine positive or negative message based on confidence
                action_type = 'positive' if confidence > 50 else 'negative'
                
                # Get the corresponding message from predefined actions
                return action_messages.get(predictor_key, {}).get(action_type, predictor_result.get('label', 'No Detection'))

            bnb_result = get_blynk_result('BNQ')
            qnq_result = get_blynk_result('QNQ')
            toot_result = get_blynk_result('TOOT')

            # Prepare confidence levels
            confidence_levels = {
                'bnb': safe_analysis_results.get('BNQ', {}).get('confidence', 0) / 100,
                'qnq': safe_analysis_results.get('QNQ', {}).get('confidence', 0) / 100,
                'toot': safe_analysis_results.get('TOOT', {}).get('confidence', 0) / 100
            }

            # Trigger Blynk event
            logger.info(f"Attempting to trigger Blynk event with results:")
            logger.info(f"  BNB Result: {bnb_result}")
            logger.info(f"  QNQ Result: {qnq_result}")
            logger.info(f"  TOOT Result: {toot_result}")
            logger.info(f"  Confidence Levels: {json.dumps(confidence_levels, indent=2)}")

            from django.conf import settings
            VIRTUAL_PINS = settings.BLYNK_VIRTUAL_PINS
            # Import Blynk connection if not already passed
            from .blynk_utils import blynk_connection as default_blynk_connection

            # Use passed connection or default connection
            active_blynk_connection = blynk_connection or default_blynk_connection

            # Check if a valid Blynk connection exists
            if active_blynk_connection and hasattr(active_blynk_connection, 'trigger_notification'):
                trigger_blynk_event(
                    bnb_result=bnb_result, 
                    qnq_result=qnq_result, 
                    toot_result=toot_result,
                    spectrogram_path=spectrograms[0] if spectrograms else None,
                    confidence_levels=confidence_levels,
                    blynk_connection=active_blynk_connection
                )
            else:
                logger.warning("No valid Blynk connection available for notifications")
        except Exception as blynk_error:
            logger.error(f"Error triggering Blynk event: {blynk_error}")
            logger.error(traceback.format_exc())

        # Send notification to Discord with analysis results
        try:
            # Format the message with prediction results in JSON-like format
            message = "**BeemoDos Analysis Results**\n"
            message += "```json\n{"
            
            # Add BNB result if available
            if 'BNQ' in analysis_results:
                message += '\n  "BNB Prediction": {'
                message += '\n    "File": "' + (spectrograms[0] if spectrograms else "Unknown") + '",'  
                message += '\n    "Predicted": "' + analysis_results["BNQ"]["label"] + '",'  
                message += '\n    "Confidence": ' + str(analysis_results["BNQ"]["confidence"]) + ','  
                message += '\n    "Predicted Class": ' + str(analysis_results["BNQ"]["predicted_class"]) + ','  
                message += '\n    "F1 Score": ' + str(analysis_results.get("BNQ", {}).get('f1_score', 'N/A')) + ','  
                message += '\n    "Precision": ' + str(analysis_results["BNQ"]["precision"]) + ''  
                message += '\n  }'
            
            # Add QNQ result if available
            if 'QNQ' in analysis_results:
                if 'BNQ' in analysis_results:  # Add comma if BNQ was included
                    message += ","
                message += '\n  "QNQ Prediction": {'
                message += '\n    "File": "' + (spectrograms[0] if spectrograms else "Unknown") + '",'  
                message += '\n    "Predicted": "' + analysis_results["QNQ"]["label"] + '",'  
                message += '\n    "Confidence": ' + str(analysis_results["QNQ"]["confidence"]) + ','  
                message += '\n    "Predicted Class": ' + str(analysis_results["QNQ"]["predicted_class"]) + ','  
                message += '\n    "F1 Score": ' + str(analysis_results.get("QNQ", {}).get('f1_score', 'N/A')) + ','  
                message += '\n    "Precision": ' + str(analysis_results["QNQ"]["precision"]) + ''  
                message += '\n  }'
            
            # Add TOOT result if available
            if 'TOOT' in analysis_results:
                if 'BNQ' in analysis_results or 'QNQ' in analysis_results:  # Add comma if previous results were included
                    message += ","
                message += '\n  "TOOT Prediction": {'
                message += '\n    "File": "' + (spectrograms[0] if spectrograms else "Unknown") + '",'  
                message += '\n    "Predicted": "' + analysis_results["TOOT"]["label"] + '",'  
                message += '\n    "Confidence": ' + str(analysis_results["TOOT"]["confidence"]) + ','  
                message += '\n    "Predicted Class": ' + str(analysis_results["TOOT"]["predicted_class"]) + ','  
                message += '\n    "F1 Score": ' + str(analysis_results.get("TOOT", {}).get('f1_score', 'N/A')) + ','  
                message += '\n    "Precision": ' + str(analysis_results["TOOT"]["precision"]) + ''  
                message += '\n  }'
            
            message += '\n}\n```\n'
            
            # Add recording analysis information
            message += "**Recording Analysis**\n"
            
            # Try to extract frequency information if available
            try:
                # Calculate frequency information from the audio file
                if spectrograms and len(spectrograms) > 0:
                    # Get the audio file path from the spectrogram path
                    spectrogram_path = spectrograms[0]
                    logger.info(f"Attempting frequency analysis for spectrogram: {spectrogram_path}")
                    
                    # Extract session directory from spectrogram path
                    # Format appears to be: recordings/20250313_152709/BNQ_spectrogram_1.png
                    match = re.match(r'recordings/(\d+_\d+)/', spectrogram_path)
                    if match:
                        session_dir = match.group(1)
                        audio_dir = os.path.join(settings.MEDIA_ROOT, 'recordings', session_dir)
                        logger.info(f"Looking for audio files in: {audio_dir}")
                        
                        # Look for WAV files in the session directory
                        if os.path.exists(audio_dir):
                            audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.wav')]
                            logger.info(f"Found audio files in {audio_dir}: {audio_files}")
                            
                            if audio_files:
                                # Use the first audio file found
                                audio_path = os.path.join(audio_dir, audio_files[0])
                                logger.info(f"Using audio file for analysis: {audio_path}")
                                
                                # Load the audio file
                                sample_rate, samples = wavfile.read(audio_path)
                                
                                # Convert stereo to mono if needed
                                if len(samples.shape) > 1 and samples.shape[1] > 1:
                                    samples = np.mean(samples, axis=1)
                                
                                # Perform FFT
                                fft_data = np.fft.fft(samples)
                                frequencies = np.fft.fftfreq(len(samples), 1/sample_rate)
                                
                                # Filter out low-frequency noise (below 20 Hz)
                                MIN_FREQUENCY = 20
                                mask = np.abs(frequencies) >= MIN_FREQUENCY
                                filtered_freqs = frequencies[mask]
                                filtered_fft = np.abs(fft_data[mask])
                                
                                # Compute frequency statistics
                                if len(filtered_freqs) > 0 and len(filtered_fft) > 0:
                                    # Find the index of the maximum amplitude in the filtered FFT data
                                    max_idx = np.argmax(filtered_fft)
                                    peak_freq = filtered_freqs[max_idx]
                                    avg_freq = np.mean(np.abs(filtered_freqs))
                                    
                                    # Compute RMS amplitude for activity classification
                                    rms_amplitude = np.sqrt(np.mean(samples**2)) / 32768.0
                                    
                                    # Classify activity level based on frequency and amplitude
                                    if avg_freq < 100:
                                        base_level = "Low"
                                    elif 100 <= avg_freq <= 300:
                                        base_level = "Normal"
                                    elif 300 < avg_freq <= 500:
                                        base_level = "High"
                                    else:
                                        base_level = "Chaotic"
                                    
                                    # Amplitude-based refinement
                                    if rms_amplitude < 0.1:
                                        activity = f"Very {base_level}"
                                    elif 0.1 <= rms_amplitude < 0.3:
                                        activity = f"{base_level}"
                                    elif 0.3 <= rms_amplitude < 0.6:
                                        activity = f"Intense {base_level}"
                                    else:
                                        activity = f"Extremely {base_level}"
                                    
                                    # Add frequency information to the message
                                    message += "Frequency Data: Average " + str(avg_freq) + "Hz, Peak " + str(peak_freq) + "Hz\n"
                                    message += "Activity Level: " + activity + " Activity\n"
                                    
                                    logger.info(f"Frequency analysis complete: Avg={avg_freq}Hz, Peak={peak_freq}Hz, Activity={activity}")
                                else:
                                    logger.warning("No valid frequency data found after filtering")
                                    message += "Frequency Data: No valid frequency data found\n"
                                    message += "Activity Level: Unknown\n"
                            else:
                                logger.warning(f"No audio files found in directory: {audio_dir}")
                                message += "Frequency Data: No audio files found\n"
                                message += "Activity Level: Unknown\n"
                        else:
                            logger.warning(f"Audio directory not found: {audio_dir}")
                            message += "Frequency Data: Audio directory not found\n"
                            message += "Activity Level: Unknown\n"
                    else:
                        logger.warning(f"Could not extract session directory from path: {spectrogram_path}")
                        message += "Frequency Data: Could not locate audio file\n"
                        message += "Activity Level: Unknown\n"
                else:
                    logger.warning("No spectrograms available for frequency analysis")
                    message += "Frequency Data: No spectrograms available\n"
                    message += "Activity Level: Unknown\n"       
            except Exception as e:
                logger.error(f"Error in frequency analysis: {e}")
                logger.error(traceback.format_exc())
                message += "Frequency Data: Error during analysis\n"
                message += "Activity Level: Unknown\n"
            
            # Add interpretation and recommendations based on predictions
            message += "\n**Interpretation & Recommendations**\n"
            
            # BNQ interpretation
            if 'BNQ' in analysis_results:
                bnq_class = analysis_results['BNQ']['predicted_class']
                bnq_confidence = analysis_results['BNQ']['confidence']
                if bnq_class == 1 and bnq_confidence > 50:
                    message += "**Bees Detected**: Hive is active. Continue regular monitoring.\n"
                else:
                    message += "**Low Bee Activity**: Consider checking for potential issues.\n"
            
            # QNQ interpretation
            if 'QNQ' in analysis_results:
                qnq_class = analysis_results['QNQ']['predicted_class']
                qnq_confidence = analysis_results['QNQ']['confidence']
                if qnq_class == 1 and qnq_confidence > 50:
                    message += "**Queen Detected**: Queen is present and active.\n"
                else:
                    message += "**No Queen Detected**: Consider checking queen status.\n"
            
            # TOOT interpretation
            if 'TOOT' in analysis_results:
                toot_class = analysis_results['TOOT']['predicted_class']
                toot_confidence = analysis_results['TOOT']['confidence']
                if toot_class == 1 and toot_confidence > 50:
                    message += "**Tooting Detected**: Potential queen emergence or competition.\n"
                else:
                    message += "**No Tooting**: Normal hive sounds detected.\n"
            
            # Add link to web interface
            message += "\n[View Full Analysis on BeemoDos Dashboard](http://localhost:8000/audio_analyzer/)\n"
            
            # Get the path to the spectrogram image
            spectrogram_path = None
            if spectrograms and len(spectrograms) > 0:
                spectrogram_path = os.path.join(settings.MEDIA_ROOT, spectrograms[0])
            
            # Prepare notification messages with detailed insights
            def generate_notification_message(predictor_key, predictor_result):
                confidence = predictor_result.get('confidence', 0)
                label = predictor_result.get('label', 'No Detection')
                
                notification_templates = {
                    'BNQ': {
                        'positive': f"🐝 Hive Buzz Alert: Active Bee Presence Detected (Confidence: {confidence:.2f}%)\n"
                                   f"Observation: Significant buzzing indicates healthy hive activity. Continue regular monitoring.",
                        'negative': f"🐝 Hive Status: Low Bee Activity (Confidence: {confidence:.2f}%)\n"
                                    f"Recommendation: Inspect the hive for potential issues or reduced bee population."
                    },
                    'QNQ': {
                        'positive': f"👑 Queen Bee Confirmation: Presence Detected (Confidence: {confidence:.2f}%)\n"
                                    f"Status: Queen bee is present, suggesting a stable and potentially productive hive.",
                        'negative': f"👑 Queen Bee Alert: Potential Absence (Confidence: {confidence:.2f}%)\n"
                                    f"Caution: Consider preparing to introduce a new queen to maintain hive health."
                    },
                    'TOOT': {
                        'positive': f"🔊 Queen Bee Tooting Detected (Confidence: {confidence:.2f}%)\n"
                                    f"Insight: Potential queen emergence or competitive behavior observed. Monitor closely.",
                        'negative': f"🔊 Queen Communication: No Tooting Detected (Confidence: {confidence:.2f}%)\n"
                                    f"Current Status: No significant queen communication signals at this time."
                    }
                }
                
                action_type = 'positive' if confidence > 50 else 'negative'
                return notification_templates.get(predictor_key, {}).get(action_type, f"Detection for {predictor_key}: {label}")

            # Generate detailed notification messages
            notification_messages = {
                predictor_key: generate_notification_message(predictor_key, safe_analysis_results.get(predictor_key, {}))
                for predictor_key in ['BNQ', 'QNQ', 'TOOT']
            }

            # Combine all notification messages
            full_notification_message = "\n\n".join(notification_messages.values())

            # Send the message to Discord
            discord_result = send_discord_message(full_notification_message, spectrogram_path)
            
            if discord_result:
                logger.info("Successfully sent analysis results to Discord")
            else:
                logger.warning("Failed to send message to Discord")
        except Exception as discord_error:
            logger.error(f"Error sending Discord notification: {discord_error}")
            logger.error(traceback.format_exc())
            # Continue processing even if Discord notification fails

        # Prepare final response with additional metadata
        # Convert NumPy types to native Python types for JSON serialization
        serializable_results = {}
        for predictor_name, predictor_data in analysis_results.items():
            serializable_results[predictor_name] = {}
            for key, value in predictor_data.items():
                # Convert NumPy types to native Python types
                if hasattr(value, 'item') and callable(getattr(value, 'item')):
                    serializable_results[predictor_name][key] = value.item()
                elif isinstance(value, (list, tuple)):
                    # Convert each item in the list/tuple if needed
                    serializable_results[predictor_name][key] = [
                        item.item() if hasattr(item, 'item') and callable(getattr(item, 'item')) else item
                        for item in value
                    ]
                else:
                    serializable_results[predictor_name][key] = value
        
        response_data = {
            'success': True,
            'recording_count': 1,  # Assuming single recording
            'status': 'Processed successfully',
            'analysis_results': serializable_results
        }

        # Log the entire response for verification
        logger.info(f"Complete Response: {json.dumps(response_data, indent=2)}")

        return JsonResponse(response_data)
    
    except Exception as e:
        logger.error(f"Audio analysis error: {str(e)}")
        return JsonResponse({
            'success': False,
            'recording_count': 0,
            'status': 'Processing failed',
            'error': str(e)
        }, status=500)

@csrf_exempt
def retrain_model(request):
    """
    Endpoint to retrain machine learning models based on user feedback
    
    Expects JSON payload with:
    - model_type: 'bnq', 'qnq', or 'toot'
    - true_label: 0 or 1
    - spectrogram_path: relative path to the spectrogram image from media directory
    """
    # Use Django's settings to get the media root path
    MEDIA_BASE_PATH = settings.MEDIA_ROOT

    try:
        if request.method == 'POST':
            # Try parsing JSON from different sources
            try:
                data = json.loads(request.body.decode('utf-8'))
            except json.JSONDecodeError:
                try:
                    data = request.POST.dict()
                except Exception:
                    data = request.data if hasattr(request, 'data') else {}
            
            # Log received data for debugging
            logger.info(f"Received retraining data: {data}")

            # Extract and validate parameters
            model_type = str(data.get('model_type', '')).lower().strip()
            true_label = data.get('true_label')
            spectrogram_path = data.get('spectrogram_path', '')

            # Clean spectrogram path by removing URL prefixes
            if spectrogram_path.startswith('http://') or spectrogram_path.startswith('https://'):
                from urllib.parse import urlparse
                parsed_url = urlparse(spectrogram_path)
                spectrogram_path = parsed_url.path

            # Remove '/media/' prefix if present
            if spectrogram_path.startswith('/media/'):
                spectrogram_path = spectrogram_path.replace('/media/', '', 1)

            # Detailed parameter validation
            errors = []
            if not model_type:
                errors.append("'model_type' is required")
            elif model_type not in ['bnq', 'qnq', 'toot']:
                errors.append("'model_type' must be 'bnq', 'qnq', or 'toot'")
            
            if true_label is None:
                errors.append("'true_label' is required")
            elif true_label not in [0, 1]:
                errors.append("'true_label' must be 0 or 1")
            
            # Validate spectrogram path
            if not spectrogram_path:
                errors.append("'spectrogram_path' is required")
            
            # Construct full local path
            full_spectrogram_path = os.path.join(MEDIA_BASE_PATH, spectrogram_path)

            # Validate file existence
            if not os.path.exists(full_spectrogram_path):
                errors.append(f"Spectrogram file not found: {full_spectrogram_path}")
                logger.error(f"File not found: {full_spectrogram_path}")
                logger.error(f"Original path: {data.get('spectrogram_path')}")
                logger.error(f"Cleaned path: {spectrogram_path}")
                logger.error(f"Media Base Path: {MEDIA_BASE_PATH}")

            # Return detailed error if any
            if errors:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Invalid or missing parameters',
                    'details': errors
                }, status=400)

            # Dynamically import the correct retraining function
            try:
                # Select retraining function based on model type
                if model_type == 'bnq':
                    from predictors.BNBpredictor import manual_set_true_label_and_retrain as retrain_func
                elif model_type == 'qnq':
                    from predictors.QNQpredictor import manual_set_true_label_and_retrain as retrain_func
                elif model_type == 'toot':
                    from predictors.TOOTpredictor import manual_set_true_label_and_retrain as retrain_func
                else:
                    raise ValueError(f"Unsupported model type: {model_type}")

                # Perform retraining
                retrain_func(true_label, full_spectrogram_path)
                
                # Optional: Send Discord notification about model retraining
                try:
                    notification_message = (
                        f"🔄 Model Retraining Completed\n"
                        f"Model: {model_type.upper()}\n"
                        f"True Label: {true_label}\n"
                        f"Spectrogram: {spectrogram_path}"
                    )
                    send_discord_message(notification_message)
                except Exception as discord_error:
                    logger.warning(f"Failed to send Discord notification for model retraining: {discord_error}")
                
                return JsonResponse({
                    'status': 'success', 
                    'message': f'{model_type.upper()} model retrained successfully',
                    'details': {
                        'model_type': model_type,
                        'true_label': true_label,
                        'spectrogram_path': full_spectrogram_path
                    }
                })
            
            except ImportError as import_error:
                logger.error(f"Import error for {model_type} retraining: {import_error}")
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Failed to import retraining module for {model_type}',
                    'details': str(import_error)
                }, status=500)
            
            except Exception as retraining_error:
                logger.error(f"Retraining error: {str(retraining_error)}")
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Failed to retrain model',
                    'details': str(retraining_error)
                }, status=500)

        else:
            # Handle unsupported HTTP methods
            return JsonResponse({
                'status': 'error', 
                'message': 'Only POST method is allowed'
            }, status=405)

    except Exception as e:
        logger.error(f"Unexpected error in model retraining: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': 'Unexpected error processing retraining request',
            'details': str(e)
        }, status=500)

@csrf_exempt
def send_discord_notification(request):
    """
    API endpoint to send a notification to Discord
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        image_path = data.get('image_path', None)
        
        if not message:
            return JsonResponse({'success': False, 'error': 'Message is required'}, status=400)
        
        # Validate image path if provided
        if image_path and not os.path.exists(image_path):
            return JsonResponse({'success': False, 'error': 'Image file not found'}, status=404)
        
        # Send to Discord
        result = send_discord_message(message, image_path)
        
        if result:
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to send message'}, status=500)
    except Exception as e:
        logger.error(f'Error in send_discord_notification: {e}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def test_discord(request):
    """
    Simple endpoint to test Discord notification
    """
    try:
        logger.info("Testing Discord notification")
        message = "This is a test message from BeemoDos"
        
        # Send the message to Discord
        result = send_discord_message(message)
        
        if result:
            return JsonResponse({'success': True, 'message': 'Discord notification sent successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Failed to send Discord notification'}, status=500)
    except Exception as e:
        logger.error(f"Error in test_discord: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def test_blynk(request):
    """
    Test Blynk connection and functionality
    """
    try:
        # Send a test notification
        notification_result = blynk_connection.trigger_notification(
            "Blynk Test", 
            "test_event", 
            "Blynk connection test from BeemoDos"
        )
        
        # Send data to a virtual pin
        pin_result = blynk_connection.send_string_to_blynk(1, "Blynk test data")
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Blynk connection test completed',
            'notification_sent': notification_result,
            'pin_data_sent': pin_result,
            'connection_status': blynk_connection.is_connected
        })
    except Exception as e:
        logger.error(f"Blynk connection test failed: {e}")
        return JsonResponse({
            'status': 'error', 
            'message': f'Blynk connection test failed: {str(e)}',
            'connection_status': blynk_connection.is_connected
        }, status=500)

@csrf_exempt
def test_blynk_connection(request):
    """
    Test Blynk connection and virtual pin 3 functionality
    
    Returns a JSON response indicating the connection status
    """
    try:
        # Test V3 connection
        connection_result = blynk_connection.test_v3_connection()
        
        return JsonResponse({
            'status': 'success',
            'connection_test': connection_result,
            'message': 'Blynk V3 connection test completed' if connection_result else 'Blynk V3 connection test failed'
        })
    
    except Exception as e:
        logger.error(f"Blynk connection test error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

import json
import logging
from .blynk_utils import blynk_connection  # Import the global Blynk connection

logger = logging.getLogger(__name__)

from django.conf import settings

def trigger_blynk_event(
    bnb_result=None, 
    qnq_result=None, 
    toot_result=None, 
    spectrogram_path=None,
    confidence_levels=None, 
    frequency_data=None,
    blynk_connection=None,
    **kwargs
):
    # Ensure settings are imported
    from django.conf import settings
    
    if not hasattr(settings, 'BLYNK_VIRTUAL_PINS'):
        logger.error("Blynk virtual pins not configured in settings")
        return False

    VIRTUAL_PINS = settings.BLYNK_VIRTUAL_PINS

    try:
        # Trigger Blynk event based on prediction
        if bnb_result and bnb_result.lower().startswith('Hive Activity Confirmed. Continue regular monitoring.'):
            blynk_connection.trigger_notification(
                event_name="[Hive 1] Bees are Present Inside your Hive",
                event_code="bees_detected",
                description="Bee activity detected in Hive 1."
            )
        elif bnb_result:
            blynk_connection.trigger_notification(
                event_name="[Hive 1] There are No Bees Inside your Hive!",
                event_code="no_bees",
                description="No bees detected in Hive 1."
            )

        if qnq_result and qnq_result.lower().startswith('queen bee presence confirmed'):
            blynk_connection.trigger_notification(
                event_name="[Hive 1] Queen Bee Presence Confirmed",
                event_code="queen_present",
                description="Queen bee present in Hive 1."
            )
        elif qnq_result:
            blynk_connection.trigger_notification(
                event_name="[Hive 1] Queen Bee Absence Alert",
                event_code="queen_absent",
                description="Queen bee absent in Hive 1."
            )

        if toot_result and toot_result.lower().startswith('queen tooting detected'):
            blynk_connection.trigger_notification(
                event_name="[Hive 1] Queen Bee Tooting Detected",
                event_code="queen_toot_detected",
                description="Queen bee tooting detected in Hive 1."
            )

    except Exception as blynk_event_error:
        logger.error(f"Error triggering Blynk event notifications: {blynk_event_error}")

    # Rest of the existing function logic continues here...

def diagnose_audio_devices():
    """
    Enhanced audio device diagnosis with comprehensive error handling and logging
    """
    import sounddevice as sd
    import traceback
    import sys
    
    # Detailed system and library information logging
    logger.info("Python Version: %s", sys.version)
    logger.info("Platform: %s", sys.platform)
    
    try:
        # Get all devices from sounddevice
        try:
            all_devices = sd.query_devices()
            logger.info(f"Total devices found: {len(all_devices)}")
            
            # Comprehensive device detection
            detected_devices = []
            usb_input_devices = []
            
            for i, device in enumerate(all_devices):
                try:
                    # Log details for ALL devices, not just input devices
                    device_info = {
                        'index': i,
                        'name': device.get('name', 'Unknown Device'),
                        'input_channels': device.get('max_input_channels', 0),
                        'output_channels': device.get('max_output_channels', 0),
                        'default_samplerate': device.get('default_samplerate', 'Unknown')
                    }
                    
                    # Log detailed device information
                    logger.info(f"Device {i}: {device_info}")
                    
                    # Still track devices with input channels
                    if device.get('max_input_channels', 0) > 0:
                        detected_devices.append(i)
                        
                        # Prioritize USB devices
                        if ('usb' in device.get('name', '').lower() or 
                            'pnp' in device.get('name', '').lower()):
                            usb_input_devices.append(i)
                
                except Exception as device_error:
                    logger.error(f"Error processing device {i}: {device_error}")
            
            # Prioritize USB devices if available
            if usb_input_devices:
                logger.info(f"Prioritizing USB input devices: {usb_input_devices}")
                return usb_input_devices, [
                    {
                        'index': usb_input_devices[0],
                        'name': sd.query_devices(usb_input_devices[0])['name'],
                        'max_input_channels': sd.query_devices(usb_input_devices[0])['max_input_channels']
                    }
                ]
            
            # Fallback to all detected input devices
            if detected_devices:
                logger.info(f"Using first available input device: {detected_devices[0]}")
                return detected_devices, [
                    {
                        'index': detected_devices[0],
                        'name': sd.query_devices(detected_devices[0])['name'],
                        'max_input_channels': sd.query_devices(detected_devices[0])['max_input_channels']
                    }
                ]
            
            # No devices found
            logger.error("No input devices detected")
            return [], []
        
        except Exception as all_devices_error:
            logger.error(f"Comprehensive device detection error: {all_devices_error}")
            logger.error(traceback.format_exc())
            return [], []
    
    except ImportError:
        logger.error("Sounddevice library not installed")
        return [], []
    except Exception as unexpected_error:
        logger.error(f"Unexpected error in audio device diagnosis: {unexpected_error}")
        logger.error(traceback.format_exc())
        return [], []

def record_and_analyze_audio(request):
    """
    Record audio from the first available input device and analyze it.
    
    Provides comprehensive error handling and device detection.
    """
    try:
        # Diagnose available audio devices
        input_devices, device_details = diagnose_audio_devices()
        
        # Check if any input devices are available
        if not input_devices:
            error_message = "No audio input devices detected. Please connect a microphone or audio input device."
            logger.error(error_message)
            return JsonResponse({
                'status': 'error', 
                'message': error_message,
                'diagnostic_info': {
                    'total_devices': len(sd.query_devices()),
                    'input_devices': device_details
                }
            }, status=400)
        
        # Use the first available input device (prioritizing USB)
        device_index = input_devices[0]
        logger.info(f"Using audio input device: {device_details[0]['name']} (Index: {device_index})")
        
        # Rest of the existing recording logic remains the same
        duration = request.POST.get('duration', 5)  # Default 5 seconds
        sample_rate = request.POST.get('sample_rate', 44100)  # Default 44.1 kHz
        
        # Record audio from specified device
        recording = sd.rec(
            int(duration * sample_rate), 
            samplerate=sample_rate, 
            channels=1, 
            dtype='float64',
            device=device_index
        )
        sd.wait()
        
        # Save recording
        audio_filename = f'bee_recording_{""}.wav'
        audio_path = os.path.join(settings.MEDIA_ROOT, audio_filename)
        
        # Ensure media directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        
        # Write audio file using scipy
        wavfile.write(audio_path, sample_rate, (recording * 32767).astype(np.int16))
        
        # Perform frequency analysis
        frequency_results = analyze_audio_frequency(audio_path, sample_rate)
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Audio recorded and analyzed successfully',
            'filename': audio_filename,
            'device': device_index,
            'frequency_analysis': frequency_results
        })
    
    except Exception as e:
        logger.error(f"Audio recording and analysis error: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)

def analyze_audio_frequency(audio_path, sample_rate):
    """
    Perform frequency analysis on the recorded audio
    
    :param audio_path: Path to the audio file
    :param sample_rate: Sampling rate of the audio
    :return: Dictionary of frequency analysis results
    """
    try:
        # Load audio file
        y, sr = librosa.load(audio_path)
        
        # Compute spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        
        # Compute dominant frequency
        fft = np.fft.fft(y)
        frequencies = np.fft.fftfreq(len(y), 1/sr)
        
        # Filter out low-frequency noise (below 20 Hz)
        MIN_FREQUENCY = 20
        mask = np.abs(frequencies) >= MIN_FREQUENCY
        filtered_freqs = frequencies[mask]
        filtered_fft = np.abs(fft[mask])
        
        # Compute frequency range
        frequency_range = (np.min(frequencies[frequencies > 0]), np.max(frequencies))
        
        # Prepare frequency data for Google Sheets
        frequency_data = {
            'dominant_frequency': round(np.max(filtered_freqs), 2),
            'frequency_range': f"{round(frequency_range[0], 2)} - {round(frequency_range[1], 2)}",
            'spectral_centroid': round(np.mean(spectral_centroid), 2),
            'spectral_bandwidth': round(np.mean(spectral_bandwidth), 2),
            'spectral_rolloff': round(np.mean(spectral_rolloff), 2)
        }
        
        # Save frequency data to Google Sheets
        save_frequency_to_sheets(frequency_data)
        
        return frequency_data
    
    except Exception as e:
        logger.error(f"Frequency analysis error: {str(e)}")
        return None
