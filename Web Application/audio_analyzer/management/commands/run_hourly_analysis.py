import os
import logging
import sounddevice as sd
import soundfile as sf
import numpy as np
from django.core.management.base import BaseCommand
from django.conf import settings
from audio_analyzer.views import analyze_audio
from django.http import HttpRequest

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Perform hourly audio recording and analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--duration', 
            type=int, 
            default=10, 
            help='Duration of audio recording in seconds (default: 10)'
        )
        parser.add_argument(
            '--device', 
            type=int, 
            default=None, 
            help='Audio input device index. Use "python -m sounddevice" to list devices.'
        )
        parser.add_argument(
            '--sample-rate', 
            type=int, 
            default=None, 
            help='Custom sample rate (default: project settings)'
        )
        parser.add_argument(
            '--channels', 
            type=int, 
            default=1, 
            help='Number of audio channels (default: 1)'
        )

    def handle(self, *args, **options):
        """
        Perform audio recording and analysis with configurable parameters
        """
        try:
            # Logging start of hourly analysis
            logger.info("Starting hourly audio analysis")

            # Determine recording parameters
            duration = options['duration']
            device = options['device']
            sample_rate = options['sample_rate'] or getattr(settings, 'SAMPLE_RATE', 44100)
            channels = options['channels']

            # Log selected recording parameters
            logger.info(f"Recording Configuration:")
            logger.info(f"  Duration: {duration} seconds")
            logger.info(f"  Sample Rate: {sample_rate} Hz")
            logger.info(f"  Channels: {channels}")
            
            # List available devices if no specific device is selected
            if device is None:
                devices = sd.query_devices()
                logger.info("Available Audio Devices:")
                for idx, dev in enumerate(devices):
                    logger.info(f"  Device {idx}: {dev['name']}")
                
                # Try to automatically select default input device
                try:
                    default_input = sd.default.device[0]
                    logger.info(f"Using default input device: {default_input}")
                    device = default_input
                except Exception as e:
                    logger.warning(f"Could not select default input device: {e}")

            # Create a mock HttpRequest for the analyze_audio function
            request = HttpRequest()
            request.method = 'POST'

            # Create media directory if it doesn't exist
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

            # Generate unique filename for this recording
            audio_filename = "hourly_recording_.wav"
            audio_path = os.path.join(settings.MEDIA_ROOT, audio_filename)

            # Record audio
            logger.info(f"Recording audio for {duration} seconds")
            try:
                recording = sd.rec(
                    int(duration * sample_rate), 
                    samplerate=sample_rate, 
                    channels=channels, 
                    dtype='float32',
                    device=device
                )
                sd.wait()  # Wait until recording is finished
                sf.write(audio_path, recording, sample_rate)
            except Exception as recording_error:
                logger.error(f"Audio recording failed: {recording_error}")
                raise

            logger.info(f"Audio recorded to {audio_path}")

            # Set the audio file in the request
            request.FILES['audio'] = audio_path

            # Perform analysis
            response = analyze_audio(request)

            # Log analysis results
            if hasattr(response, 'content'):
                logger.info("Hourly analysis completed successfully")
                
                # Parse and log the response content for more details
                try:
                    import json
                    response_data = json.loads(response.content.decode('utf-8'))
                    
                    # Log specific details from the response
                    logger.info("Analysis Details:")
                    for predictor in ['BNQ', 'QNQ', 'TOOT']:
                        if predictor in response_data:
                            logger.info(f"{predictor} Prediction:")
                            logger.info(f"  Predicted Class: {response_data[predictor].get('predicted_class', 'N/A')}")
                            logger.info(f"  Confidence: {response_data[predictor].get('confidence', 'N/A')}%")
                            logger.info(f"  Label: {response_data[predictor].get('label', 'N/A')}")
                except Exception as parse_error:
                    logger.warning(f"Could not parse response content: {parse_error}")
                
                # Verify Blynk and Discord notification status
                if 'blynk_notification_sent' in response_data:
                    logger.info("Blynk Notification: Sent Successfully")
                else:
                    logger.warning("Blynk Notification: Not Sent")
                
                if 'discord_notification_sent' in response_data:
                    logger.info("Discord Notification: Sent Successfully")
                else:
                    logger.warning("Discord Notification: Not Sent")
            
            else:
                logger.warning("Hourly analysis did not return a valid response")

        except Exception as e:
            logger.error(f"Error during hourly audio analysis: {e}", exc_info=True)

        self.stdout.write(self.style.SUCCESS('Hourly audio analysis completed'))