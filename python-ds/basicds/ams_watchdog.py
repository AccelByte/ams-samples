"""
AccelByte Multiplayer Servers (AMS) Watchdog Protocol Client

This module implements the AMS watchdog protocol for dedicated servers.
Reference: https://docs.accelbyte.io/gaming-services/services/ams/AMS-watchdog-protocol/
"""

import json
import threading
import time
import logging
from typing import Optional, Callable
from websocket import WebSocketApp

logger = logging.getLogger(__name__)


class AMSWatchdogClient:
    """
    Client for communicating with the AMS watchdog using the official protocol.
    
    The watchdog expects:
    - WebSocket connection to ws://localhost:5555/watchdog
    - DS ID in the 'ams-dsid' header
    - Ready message when server is ready for allocation
    - Heartbeat messages every 15 seconds
    - Proper handling of drain messages
    """
    
    def __init__(self, ds_id: str, watchdog_url: str = "ws://localhost:5555/watchdog"):
        self.ds_id = ds_id
        self.watchdog_url = watchdog_url
        self.ws: Optional[WebSocketApp] = None
        self.connected = False
        self.ready_sent = False
        self.drain_received = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_heartbeat = threading.Event()
        
        # Callbacks
        self.on_drain: Optional[Callable[[], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
    
    def connect(self) -> bool:
        """
        Connect to the AMS watchdog with the DS ID header.
        Returns True if connection is successful, False otherwise.
        """
        try:
            headers = {"ams-dsid": self.ds_id}
            
            self.ws = WebSocketApp(
                self.watchdog_url,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            logger.info(f"Connecting to AMS watchdog at {self.watchdog_url} with DS ID: {self.ds_id}")
            
            # Run in a separate thread to avoid blocking
            def run_websocket():
                try:
                    self.ws.run_forever()
                except Exception as e:
                    logger.error(f"WebSocket run_forever exception: {e}")
                    logger.error(f"Exception type: {type(e)}")
            
            ws_thread = threading.Thread(target=run_websocket, daemon=True)
            ws_thread.start()
            
            # Wait for connection (with timeout)
            for _ in range(50):  # 5 seconds timeout
                if self.connected:
                    return True
                time.sleep(0.1)
            
            logger.error("Failed to connect to AMS watchdog within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to AMS watchdog: {e}")
            return False
    
    def send_ready(self) -> bool:
        """
        Send the 'ready' message to indicate the DS is ready for allocation.
        Should be called once the server has completed startup.
        """
        if not self.connected:
            logger.error("Cannot send ready message: not connected to watchdog")
            return False
        
        message = {
            "ready": {
                "dsid": self.ds_id
            }
        }
        
        try:
            self.ws.send(json.dumps(message))
            self.ready_sent = True
            logger.info("Sent ready message to AMS watchdog")
            return True
        except Exception as e:
            logger.error(f"Error sending ready message: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """
        Send a heartbeat message to the watchdog.
        This is called automatically every 15 seconds after connection.
        """
        if not self.connected:
            return False
        
        message = {"heartbeat": {}}
        
        try:
            self.ws.send(json.dumps(message))
            logger.debug("Sent heartbeat to AMS watchdog")
            return True
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False
    
    def reset_session_timeout(self, new_timeout_ns: Optional[int] = None) -> bool:
        """
        Reset the session timeout. Optional for most scenarios.
        
        Args:
            new_timeout_ns: New timeout in nanoseconds. If None, uses pre-configured value.
        """
        if not self.connected:
            logger.error("Cannot reset session timeout: not connected to watchdog")
            return False
        
        message = {"reset_session_timeout": {}}
        if new_timeout_ns is not None:
            message["reset_session_timeout"]["new_timeout"] = new_timeout_ns
        
        try:
            self.ws.send(json.dumps(message))
            logger.info("Sent reset session timeout message to AMS watchdog")
            return True
        except Exception as e:
            logger.error(f"Error sending reset session timeout: {e}")
            return False
    
    def disconnect(self):
        """
        Disconnect from the AMS watchdog and stop heartbeat.
        """
        logger.info("Disconnecting from AMS watchdog")
        
        # Stop heartbeat thread
        self._stop_heartbeat.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)
        
        # Close WebSocket connection
        if self.ws:
            self.ws.close()
        
        self.connected = False
    
    def _on_open(self, ws):
        """Called when WebSocket connection is opened."""
        self.connected = True
        logger.info("Connected to AMS watchdog")
        
        # Start heartbeat thread
        self._start_heartbeat()
        
        # Call user callback
        if self.on_connected:
            self.on_connected()
    
    def _on_message(self, ws, message):
        """Called when a message is received from the watchdog."""
        try:
            data = json.loads(message)
            logger.debug(f"Received message from watchdog: {data}")
            
            # Handle drain message
            if "drain" in data:
                logger.warning("Received drain signal from AMS watchdog")
                self.drain_received = True
                if self.on_drain:
                    self.on_drain()
            
        except json.JSONDecodeError:
            logger.error(f"Received invalid JSON from watchdog: {message}")
        except Exception as e:
            logger.error(f"Error handling watchdog message: {e}")
    
    def _on_error(self, ws, error):
        """Called when a WebSocket error occurs."""
        logger.error(f"AMS watchdog WebSocket error: {error}")
        logger.error(f"Error type: {type(error)}")
        if hasattr(error, 'args'):
            logger.error(f"Error args: {error.args}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket connection is closed."""
        self.connected = False
        logger.info(f"AMS watchdog connection closed: {close_status_code} - {close_msg}")
        
        # Stop heartbeat
        self._stop_heartbeat.set()
        
        # Call user callback
        if self.on_disconnected:
            self.on_disconnected()
    
    def _start_heartbeat(self):
        """Start the heartbeat thread (sends heartbeat every 15 seconds)."""
        self._stop_heartbeat.clear()
        
        def heartbeat_loop():
            while not self._stop_heartbeat.wait(15.0):  # 15 second intervals
                if self.connected:
                    self.send_heartbeat()
                else:
                    break
        
        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.debug("Started heartbeat thread")