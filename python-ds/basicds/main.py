"""
BasicDS - AccelByte Multiplayer Servers (AMS) Compatible Dedicated Server

This server implements the AMS watchdog protocol for proper integration
with AccelByte's multiplayer server infrastructure.
"""

import argparse
import logging
import signal
import sys
import time
from .ams_watchdog import AMSWatchdogClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BasicDS:
    """
    Basic Dedicated Server that implements AMS watchdog protocol.
    """
    
    def __init__(self, ds_id: str, watchdog_url: str = "ws://localhost:5555/watchdog", port: int = 7777):
        self.ds_id = ds_id
        self.port = port
        self.watchdog_client = AMSWatchdogClient(ds_id, watchdog_url)
        self.running = True
        self.in_session = False
        
        # Set up watchdog callbacks
        self.watchdog_client.on_drain = self._handle_drain
        self.watchdog_client.on_connected = self._handle_connected
        self.watchdog_client.on_disconnected = self._handle_disconnected
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self):
        """Start the dedicated server and connect to AMS watchdog."""
        logger.info(f"Starting BasicDS server with ID: {self.ds_id}")
        
        # Connect to AMS watchdog
        if not self.watchdog_client.connect():
            logger.error("Failed to connect to AMS watchdog. Exiting.")
            return False
        
        # Perform server initialization
        self._initialize_server()
        
        # Send ready signal to AMS
        if not self.watchdog_client.send_ready():
            logger.error("Failed to send ready signal to AMS watchdog")
            return False
        
        # Main server loop
        self._run_server_loop()
        
        return True
    
    def stop(self):
        """Stop the dedicated server and disconnect from watchdog."""
        logger.info("Stopping BasicDS server")
        self.running = False
        
        if self.watchdog_client:
            self.watchdog_client.disconnect()
    
    def _initialize_server(self):
        """Initialize server resources and game logic."""
        logger.info("Initializing server resources...")
        logger.info(f"Game server will listen on port {self.port}")
        
        # TODO: Add your server initialization logic here
        # Examples:
        # - Load game configuration
        # - Initialize game world
        # - Set up network listeners on self.port
        # - Load assets
        
        time.sleep(1)  # Simulate initialization time
        logger.info("Server initialization complete")
    
    def _run_server_loop(self):
        """Main server loop - handles game logic and client connections."""
        logger.info("Server is ready and running...")
        
        while self.running:
            # TODO: Add your game server logic here
            # Examples:
            # - Process client connections
            # - Update game state
            # - Handle game sessions
            # - Process player actions
            
            # For demo purposes, just sleep
            time.sleep(1)
            
            # Example of session management
            if not self.in_session:
                # Check for new session allocation from AMS
                # This would typically come through game session APIs
                pass
    
    def _handle_connected(self):
        """Called when successfully connected to AMS watchdog."""
        logger.info("Successfully connected to AMS watchdog")
    
    def _handle_disconnected(self):
        """Called when disconnected from AMS watchdog."""
        logger.warning("Disconnected from AMS watchdog") # unlikely since the connection is always to localhost
    
    def _handle_drain(self):
        """
        Handle drain signal from AMS.
        
        When AMS sends a drain signal, it means the server should:
        1. Stop accepting new game sessions
        2. Allow current sessions to complete naturally
        3. Shut down gracefully when no active sessions remain
        """
        logger.warning("Received drain signal from AMS - preparing for graceful shutdown")
        
        # TODO: Implement drain logic based on your game requirements
        # Examples:
        # - Set flag to reject new session allocations
        # - Notify players of impending server shutdown
        # - Wait for current sessions to complete
        # - Initiate graceful shutdown when ready
        
        if not self.in_session:
            # No active sessions, should shutdown immediately
            logger.info("No active sessions, shutting down immediately")
            self.stop()
        else:
            # Wait for current session to complete
            logger.info("Waiting for current session to complete before shutdown")
            # You would implement session completion monitoring here
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.stop()


def parse_arguments():
    """Parse command line arguments required by AMS."""
    parser = argparse.ArgumentParser(
        description="BasicDS - AMS Compatible Dedicated Server"
    )
    
    parser.add_argument(
        "--dsid",
        required=True,
        help="Dedicated Server ID provided by AMS (required for watchdog protocol)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=7777,
        help="Port for the game server to listen on for player connections (default: 7777)"
    )
    
    parser.add_argument(
        "--watchdog-url",
        default="ws://localhost:5555/watchdog",
        help="AMS Watchdog WebSocket URL (default: ws://localhost:5555/watchdog)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the dedicated server."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set logging level
        logging.getLogger().setLevel(getattr(logging, args.log_level))
        
        # Create and start the server
        server = BasicDS(args.dsid, args.watchdog_url, args.port)
        
        logger.info("="*50)
        logger.info("BasicDS - AccelByte AMS Compatible Server")
        logger.info("="*50)
        
        success = server.start()
        
        if not success:
            logger.error("Server failed to start properly")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()