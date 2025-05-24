from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from audio_analyzer import views as audio_analyzer_views

urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),
    
    # Audio Analyzer App URLs
    path('', include('audio_analyzer.urls')),
    
    # Explicit devices endpoint
    path('devices/', audio_analyzer_views.get_audio_devices, name='get_audio_devices'),
    
    # Multi-record endpoint
    path('audio_analyzer/multi-record/', audio_analyzer_views.record_and_generate_spectrograms, name='multi_record'),
    
    # Discord notification endpoint
    path('audio_analyzer/send-discord-notification/', audio_analyzer_views.send_discord_notification, name='audio_analyzer_discord_notification'),
    
    # Test Discord endpoint
    path('audio_analyzer/test-discord/', audio_analyzer_views.test_discord, name='audio_analyzer_test_discord'),
]

# Serve media and static files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
