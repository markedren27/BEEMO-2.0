import discord
import asyncio
import logging
import os
import json
from django.conf import settings
import aiohttp

logger = logging.getLogger('audio_analyzer.discord_utils')

def format_discord_notification(prediction_data, frequency_data=None):
    """
    Format a detailed Discord notification with prediction and frequency data
    
    :param prediction_data: Dictionary containing prediction information
    :param frequency_data: Dictionary containing frequency analysis information
    :return: Formatted notification message
    """
    # Prepare base prediction information
    notification = {
        "Prediction": {
            "Model": prediction_data.get('model', 'Unknown'),
            "Filename": prediction_data.get('filename', 'N/A'),
            "Result": prediction_data.get('prediction', 'N/A'),
            "Confidence": f"{prediction_data.get('confidence', 0):.2%}"
        }
    }
    
    # Add frequency data if available
    if frequency_data:
        notification["Frequency Analysis"] = {
            "Dominant Frequency": frequency_data.get('dominant_frequency', 'N/A'),
            "Frequency Range": frequency_data.get('frequency_range', 'N/A'),
            "Spectral Centroid": frequency_data.get('spectral_centroid', 'N/A'),
            "Spectral Bandwidth": frequency_data.get('spectral_bandwidth', 'N/A'),
            "Spectral Rolloff": frequency_data.get('spectral_rolloff', 'N/A')
        }
    
    # Convert to formatted JSON-like string
    formatted_message = "🐝 BeemoDos Analysis Report 🐝\n"
    formatted_message += "```json\n"
    formatted_message += json.dumps(notification, indent=2)
    formatted_message += "\n```"
    
    return formatted_message

async def send_discord_message_async(message, image_path=None, prediction_data=None, frequency_data=None):
    """
    Send a message to a Discord channel without running a full bot.
    This function should be called from an async context or with asyncio.run()
    
    :param message: Optional custom message
    :param image_path: Optional path to an image to attach
    :param prediction_data: Optional prediction data for detailed notification
    :param frequency_data: Optional frequency analysis data
    """
    try:
        # Get Discord configuration from settings
        token = settings.DISCORD_BOT_TOKEN
        channel_id = settings.DISCORD_CHANNEL_ID
        
        logger.info(f"Discord async function called with token length {len(token) if token else 0} and channel ID {channel_id}")
        
        if not token or channel_id == 0:
            logger.error("Discord configuration missing. Set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID in settings.")
            return False
        
        # Use async context manager for aiohttp session
        async with aiohttp.ClientSession() as session:
            # Create Discord API endpoint URL
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            
            # Prepare headers
            headers = {
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json"
            }
            
            # Prepare payload
            if prediction_data:
                # Use formatted notification if prediction data is provided
                payload = {
                    "content": format_discord_notification(
                        prediction_data, 
                        frequency_data
                    )
                }
            else:
                # Use default or custom message
                payload = {
                    "content": message or "No message provided"
                }
            
            # Send message
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    logger.info("Discord message sent successfully")
                    
                    # Send image if provided
                    if image_path and os.path.exists(image_path):
                        # Create Discord API endpoint URL for image upload
                        image_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
                        
                        # Prepare headers for image upload
                        image_headers = {
                            "Authorization": f"Bot {token}",
                            "Content-Type": "multipart/form-data"
                        }
                        
                        # Prepare payload for image upload
                        image_payload = aiohttp.FormData()
                        image_payload.add_field('file', open(image_path, 'rb'), filename=os.path.basename(image_path))
                        image_payload.add_field('payload_json', '{"content": ""}')
                        
                        # Send image
                        async with session.post(image_url, headers=image_headers, data=image_payload) as image_response:
                            if image_response.status == 200:
                                logger.info("Discord image sent successfully")
                            else:
                                logger.error(f"Failed to send Discord image. Status: {image_response.status}, Response: {await image_response.text()}")
                    
                    return True
                else:
                    logger.error(f"Failed to send Discord message. Status: {response.status}, Response: {await response.text()}")
                    return False
    
    except Exception as e:
        logger.error(f"Error in send_discord_message_async: {e}")
        return False

def send_discord_message(message, image_path=None, prediction_data=None, frequency_data=None):
    """
    Synchronous wrapper for async Discord message sending
    
    :param message: Optional custom message
    :param image_path: Optional path to an image to attach
    :param prediction_data: Optional prediction data for detailed notification
    :param frequency_data: Optional frequency analysis data
    :return: Boolean indicating message sending success
    """
    try:
        return asyncio.run(
            send_discord_message_async(
                message, 
                image_path, 
                prediction_data, 
                frequency_data
            )
        )
    except Exception as e:
        logger.error(f"Error running async Discord message: {e}")
        return False