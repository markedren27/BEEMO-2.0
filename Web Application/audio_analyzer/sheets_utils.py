import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Google Sheets configuration
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class BeemoSheetsClient:
    def __init__(self, spreadsheet_id=None, credentials_path=None, data_type=None):
        """
        Initialize Google Sheets client for BeemoDos project
        
        :param spreadsheet_id: ID of the Google Sheets document
        :param credentials_path: Path to service account credentials JSON
        :param data_type: Type of data ('frequency', 'bnb', 'qnq', 'toot')
        """
        # Default spreadsheet IDs for different data types
        self.DEFAULT_SPREADSHEETS = {
            'frequency': "1h387i_m0wb2RQ8zrO-gEwHPGzs0mp8qtgYjxXO7Gg00",
            'bnb': "1aJYoCKoo3bIkaeaC8A-AEqmNwyTzeFarOcxUo-i8cFk",
            'qnq': "1WnQ3_QtX9r7VmR6jYVu4bFgW8FV4OX8a7821KpEU4PE",
            'toot': "1xctPR54RigrpNDJDuOoUquTEeiIjgqXfeVY8DX4cmgo"
        }
        
        # Default credentials paths for different data types
        self.DEFAULT_CREDENTIALS = {
            'frequency': 'frequency_sheets_credentials.json',
            'bnb': 'bnb_sheets_credentials.json',
            'qnq': 'qnq_sheets_credentials.json',
            'toot': 'toot_sheets_credentials.json'
        }
        
        # Set spreadsheet ID
        self.spreadsheet_id = spreadsheet_id or self.DEFAULT_SPREADSHEETS.get(data_type, self.DEFAULT_SPREADSHEETS['frequency'])
        
        # Set credentials path
        if not credentials_path:
            # If no data type specified, use frequency as default
            data_type = data_type or 'frequency'
            
            credentials_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'credentials', 
                self.DEFAULT_CREDENTIALS.get(data_type, 'frequency_sheets_credentials.json')
            )
        
        self.credentials_path = credentials_path
        self.service = self._connect_to_google_sheets()

    def _connect_to_google_sheets(self):
        """
        Authenticate and connect to Google Sheets
        
        :return: Google Sheets service object
        """
        try:
            # Log detailed connection attempt information
            logger.info(f"Attempting to connect to Google Sheets with credentials from: {self.credentials_path}")
            logger.info(f"Scopes: {SCOPES}")
            
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=SCOPES
            )
            
            # Log additional credential details
            logger.info(f"Service Account Email: {creds.service_account_email}")
            
            service = build('sheets', 'v4', credentials=creds)
            return service.spreadsheets()
        except FileNotFoundError:
            logger.error(f"Credentials file not found at: {self.credentials_path}")
            return None
        except PermissionError:
            logger.error(f"Permission denied when accessing credentials file: {self.credentials_path}")
            return None
        except Exception as err:
            logger.error(f"Google Sheets connection error: {err}")
            # Log the full traceback for more detailed debugging
            import traceback
            logger.error(traceback.format_exc())
            return None

    def append_frequency_data(self, frequency_data):
        """
        Append frequency analysis data to Google Sheets
        
        :param frequency_data: Dictionary containing frequency analysis results
        :return: Response from Google Sheets API
        """
        if not self.service:
            logger.error("Google Sheets service not initialized")
            return None

        try:
            # Prepare row data with timestamp
            row_data = [
                "",  # Timestamp replaced with empty string
                frequency_data.get('dominant_frequency', 'N/A'),
                frequency_data.get('frequency_range', 'N/A'),
                frequency_data.get('spectral_centroid', 'N/A'),
                frequency_data.get('spectral_bandwidth', 'N/A'),
                frequency_data.get('spectral_rolloff', 'N/A')
            ]

            body = {'values': [row_data]}
            result = self.service.values().append(
                spreadsheetId=self.spreadsheet_id, 
                range='Sheet1!A:G',
                valueInputOption='RAW',
                body=body
            ).execute()
            return result
        except HttpError as err:
            logger.error(f"Error appending frequency data: {err}")
            return None

    def append_prediction_data(self, prediction_type, prediction_data):
        """
        Append prediction data for different models (BNB, QNQ, TOOT)
        
        :param prediction_type: Type of prediction ('bnb', 'qnq', 'toot')
        :param prediction_data: Dictionary containing prediction results
        :return: Response from Google Sheets API
        """
        if prediction_type not in self.DEFAULT_SPREADSHEETS:
            logger.error(f"Invalid prediction type: {prediction_type}")
            return None

        # Set spreadsheet ID based on prediction type
        self.spreadsheet_id = self.DEFAULT_SPREADSHEETS[prediction_type]
        
        if not self.service:
            logger.error("Google Sheets service not initialized")
            return None

        try:
            # Prepare row data with timestamp
            row_data = [
                "",  # Timestamp replaced with empty string
                prediction_data.get('filename', 'N/A'),
                prediction_data.get('prediction', 'N/A'),
                prediction_data.get('confidence', 'N/A')
            ]

            body = {'values': [row_data]}
            result = self.service.values().append(
                spreadsheetId=self.spreadsheet_id, 
                range='Sheet1!A:D',
                valueInputOption='RAW',
                body=body
            ).execute()
            return result
        except HttpError as err:
            logger.error(f"Error appending {prediction_type} prediction data: {err}")
            return None

def save_frequency_to_sheets(frequency_data):
    """
    Utility function to save frequency data to Google Sheets
    
    :param frequency_data: Dictionary of frequency analysis results
    :return: Boolean indicating success or failure
    """
    try:
        sheets_client = BeemoSheetsClient(data_type='frequency')
        result = sheets_client.append_frequency_data(frequency_data)
        
        if result:
            # Log successful save with details
            logger.info(
                f"Frequency data saved to Google Sheets successfully. "
                f"Spreadsheet ID: {sheets_client.spreadsheet_id}, "
                f"Data: {frequency_data}"
            )
            return True
        else:
            logger.warning("Failed to save frequency data to Google Sheets")
            return False
    except Exception as e:
        logger.error(f"Unexpected error saving frequency data to Google Sheets: {e}")
        return False

def save_prediction_to_sheets(prediction_type, prediction_data):
    """
    Utility function to save prediction data to Google Sheets
    
    :param prediction_type: Type of prediction ('bnb', 'qnq', 'toot')
    :param prediction_data: Dictionary of prediction results
    :return: Boolean indicating success or failure
    """
    try:
        sheets_client = BeemoSheetsClient(data_type=prediction_type)
        result = sheets_client.append_prediction_data(prediction_type, prediction_data)
        
        if result:
            # Log successful save with detailed information
            logger.info(
                f"{prediction_type.upper()} prediction data saved to Google Sheets successfully. "
                f"Spreadsheet ID: {sheets_client.spreadsheet_id}, "
                f"Filename: {prediction_data.get('filename', 'N/A')}, "
                f"Prediction: {prediction_data.get('prediction', 'N/A')}, "
                f"Confidence: {prediction_data.get('confidence', 'N/A')}"
            )
            return True
        else:
            logger.warning(f"Failed to save {prediction_type.upper()} prediction data to Google Sheets")
            return False
    except Exception as e:
        logger.error(f"Unexpected error saving {prediction_type.upper()} prediction data to Google Sheets: {e}")
        return False