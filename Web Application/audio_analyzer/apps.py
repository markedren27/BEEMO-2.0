from django.apps import AppConfig
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class AudioAnalyzerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audio_analyzer'
    verbose_name = 'Bee Audio Analyzer'

    # def ready(self):
    #     """
    #     Initialize Blynk service when the app is ready
    #     This ensures Blynk is initialized only once during app startup
    #     """
    #     if settings.BLYNK_ENABLED:
    #         try:
    #             # Import Blynk initialization function
    #             from .blynk_utils import initialize_blynk
    #             initialize_blynk()
    #             logger.info("Blynk initialized successfully during app startup")
    #         except Exception as e:
    #             logger.error(f"Failed to initialize Blynk during app startup: {e}")
    #     else:
    #         logger.info("Blynk is disabled in settings")
