import BlynkLib
import socket
import logging
import os
import threading
import time
from django.conf import settings

logger = logging.getLogger(__name__)

class BlynkConnection:
    # Define VIRTUAL_PINS as a class attribute
    VIRTUAL_PINS = settings.BLYNK_VIRTUAL_PINS

    def __init__(self, 
                 auth_token='G_3XV39JoVt7eCZnkqwdKP0dlvflgKHG', 
                 server='sgp1.blynk.cloud', 
                 port=80,  
                 firmware_version=None,
                 last_build=None):
        """
        Initialize Blynk connection with configurable parameters
        blynk_connection = BlynkConnection(server='sgp1.blynk.cloud', port=80)

        :param auth_token: Blynk authentication token
        :param server: Blynk server address
        :param port: Blynk server port (default 80 for non-SSL)
        :param firmware_version: Optional firmware version
        :param last_build: Optional last build information
        """
        self.auth_token = auth_token or os.getenv('BLYNK_AUTH_TOKEN', 'G_3XV39JoVt7eCZnkqwdKP0dlvflgKHG')
        self.server = server
        self.port = port
        self.blynk = None
        self.connection_thread = None
        self.is_connected = False
        self.heartbeat = 10
        self._stop_event = threading.Event()
        
        # Additional device information
        self.firmware_version = firmware_version
        self.last_build = last_build
        
        # Logging device details
        logger.info(f"Initializing Blynk connection:")
        logger.info(f"Server: {self.server}:{self.port}")
        if self.firmware_version:
            logger.info(f"Firmware Version: {self.firmware_version}")
        if self.last_build:
            logger.info(f"Last Build: {self.last_build}")
        
        # Initialize connection
        self.connect()

    def connect(self):
        """
        Establish connection to Blynk server with enhanced error handling
        """
        try:
            # Detailed network connectivity check
            try:
                socket.create_connection((self.server, self.port), timeout=5)
                logger.info(f"Network connectivity to {self.server}:{self.port} successful")
            except (socket.error, socket.timeout) as net_error:
                logger.error(f"Network connection failed: {net_error}")
                logger.error(f"Check network settings, firewall, and server accessibility")
                self.is_connected = False
                return

            # Initialize Blynk with detailed logging
            try:
                # Validate authentication token
                if not self.auth_token or len(self.auth_token) < 10:
                    raise ValueError("Invalid or missing Blynk authentication token")

                self.blynk = BlynkLib.Blynk(
                    self.auth_token, 
                    server=self.server, 
                    port=self.port,
                    heartbeat=self.heartbeat  # Send heartbeat every 10 seconds
                )
                
                logger.debug(f"Blynk initialized with token {self.auth_token[:5]}... on {self.server}:{self.port}")
                
                # Setup virtual pin handlers
                # Debug logging for virtual pin configuration
                logger.debug(f"Loaded Blynk Virtual Pins Configuration: {self.VIRTUAL_PINS}")
                
                @self.blynk.VIRTUAL_WRITE(self.VIRTUAL_PINS['STATUS'])
                def on_v0_write(value):
                    """
                    Handler for status virtual pin write events
                    """
                    logger.info(f"Status pin write event received: {value}")
                    logger.info(f"Current connection status: {self.is_connected}")

                @self.blynk.VIRTUAL_READ(self.VIRTUAL_PINS['STATUS'])
                def on_v0_read():
                    """
                    Handler for status virtual pin read events
                    """
                    logger.info("Status pin read event triggered")
                    try:
                        self.blynk.virtual_write(
                            self.VIRTUAL_PINS['STATUS'], 
                            f"Diagnostic read at {time.time()}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to write to status pin: {e}")

                @self.blynk.VIRTUAL_WRITE(self.VIRTUAL_PINS['BEE_PREDICTION'])
                def on_bee_prediction_write(value):
                    """
                    Handler for Bee Prediction write events
                    """
                    logger.info(f"Bee Prediction pin write event received: {value}")
                    logger.info(f"Type of value: {type(value)}")
                    logger.info(f"Full event details: {locals()}")

                @self.blynk.VIRTUAL_READ(self.VIRTUAL_PINS['BEE_PREDICTION'])
                def on_bee_prediction_read():
                    """
                    Handler for Bee Prediction read events
                    """
                    logger.info("Bee Prediction pin read event triggered")
                    return "Last known bee prediction"

                @self.blynk.VIRTUAL_WRITE(self.VIRTUAL_PINS['QUEEN_BEE_PREDICTION'])
                def on_queen_bee_prediction_write(value):
                    """
                    Handler for Queen Bee Prediction write events
                    """
                    logger.info(f"Queen Bee Prediction pin write event received: {value}")
                    logger.info(f"Type of value: {type(value)}")
                    logger.info(f"Full event details: {locals()}")

                @self.blynk.VIRTUAL_READ(self.VIRTUAL_PINS['QUEEN_BEE_PREDICTION'])
                def on_queen_bee_prediction_read():
                    """
                    Handler for Queen Bee Prediction read events
                    """
                    logger.info("Queen Bee Prediction pin read event triggered")
                    return "Last known queen bee prediction"

                @self.blynk.VIRTUAL_WRITE(self.VIRTUAL_PINS['TOOTING_PREDICTION'])
                def on_tooting_prediction_write(value):
                    """
                    Handler for Tooting Prediction write events
                    """
                    logger.info(f"Tooting Prediction pin write event received: {value}")
                    logger.info(f"Type of value: {type(value)}")
                    logger.info(f"Full event details: {locals()}")

                @self.blynk.VIRTUAL_READ(self.VIRTUAL_PINS['TOOTING_PREDICTION'])
                def on_tooting_prediction_read():
                    """
                    Handler for Tooting Prediction read events
                    """
                    logger.info("Tooting Prediction pin read event triggered")
                    return "Last known tooting prediction"
                
                # Start Blynk event loop in a separate thread
                self.connection_thread = threading.Thread(target=self._run_blynk, daemon=True)
                self.connection_thread.start()

                # Wait briefly to check initial connection status
                time.sleep(2)
                
                # Verify connection status
                if not self.is_connected:
                    logger.warning("Blynk connection failed to establish")
                    raise RuntimeError("Unable to establish Blynk connection")

                logger.info("Blynk connection initiated successfully")

            except Exception as init_error:
                logger.error(f"Blynk initialization failed: {init_error}")
                logger.error("Possible issues:")
                logger.error("1. Invalid authentication token")
                logger.error("2. Server connection problems")
                logger.error("3. Network restrictions")
                logger.error(f"Authentication token used: {self.auth_token}")
                self.is_connected = False
                raise  # Re-raise to ensure the error is not silently ignored

        except Exception as e:
            logger.error(f"Unexpected error in Blynk connection: {e}")
            self.is_connected = False
            raise  # Re-raise to ensure the error is not silently ignored

    def _run_blynk(self):
        """
        Run Blynk event loop with controlled stop mechanism
        """
        if not self.blynk:
            logger.warning("Cannot run Blynk: Not initialized")
            return

        try:
            while not self._stop_event.is_set():
                try:
                    self.blynk.run()
                    # If we reach here without an exception, we're connected
                    self.is_connected = True
                except Exception as run_error:
                    # Connection lost or other runtime error
                    logger.warning(f"Blynk connection error: {run_error}")
                    self.is_connected = False
                
                time.sleep(0.1)  # Prevent tight loop
        except Exception as e:
            logger.error(f"Blynk event loop error: {e}")
            self.is_connected = False
        finally:
            logger.info("Blynk event loop stopped")
            self.is_connected = False

    def stop(self):
        """
        Gracefully stop the Blynk connection thread
        """
        if self.connection_thread and self.connection_thread.is_alive():
            self._stop_event.set()
            self.connection_thread.join(timeout=5)
            logger.info("Blynk connection thread stopped")
            self.is_connected = False

    def send_string_to_blynk(self, pin, string):
        """
        Send a string to a specific virtual pin
        
        :param pin: Virtual pin number
        :param string: String to send
        :return: Boolean indicating success
        """
        if not self.is_connected or not self.blynk:
            logger.warning(f"Failed to send '{string}' to virtual pin V{pin}: Not connected")
            return False

        try:
            self.blynk.virtual_write(pin, string)
            logger.info(f"Sent '{string}' to virtual pin V{pin}")
            return True
        except Exception as e:
            logger.error(f"Failed to send data to Blynk: {e}")
            return False

    def trigger_notification(self, event_name, event_code, description):
        """
        Trigger a Blynk notification
        
        :param event_name: Name of the event
        :param event_code: Unique event code
        :param description: Event description
        :return: Boolean indicating success
        """
        if not self.is_connected or not self.blynk:
            logger.warning(f"Failed to trigger notification: {event_name} - {description}: Not connected")
            return False

        try:
            logger.info(f"Attempting to trigger notification: {event_name} - {description}")
            self.blynk.log_event(event_code, f"{event_name}: {description}")
            logger.info(f"Notification triggered: {event_name} - {description}")
            return True
        except Exception as e:
            logger.error(f"Failed to trigger notification: {e}")
            return False

    def test_v3_connection(self):
        """
        Test the connection and functionality of virtual pin 3
        
        This method sends a test signal to virtual pin 3 to verify 
        Blynk connection and pin responsiveness.
        
        Returns:
            bool: True if test was successful, False otherwise
        """
        if not self.blynk:
            logger.error("Blynk not initialized. Cannot test V3 connection.")
            return False
        
        try:
            # Send a test value to V3
            logger.info("Sending test signal to V3")
            self.blynk.virtual_write(self.VIRTUAL_PINS['BEE_PREDICTION'], "Test V3")
            
            # Optional: Add a small delay to allow processing
            time.sleep(1)
            
            logger.info("V3 connection test completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error testing V3 connection: {e}")
            return False

# Create a global Blynk connection instance
blynk_connection = BlynkConnection()