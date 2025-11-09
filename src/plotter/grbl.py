"""
GRBL 0.9 communication protocol implementation.
"""
import asyncio
import re
import serial
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class GRBLController:
    """GRBL 0.9 serial communication controller."""
    
    RX_BUFFER_SIZE = 127  # GRBL serial receive buffer size
    
    # GRBL error codes
    ERROR_CODES = {
        1: "G-code command letter not found",
        2: "Missing G-code value",
        3: "Invalid $-command",
        4: "Negative value for expected positive value",
        5: "Homing cycle failure",
        9: "G-code command not in homing mode",
        20: "Unsupported or invalid G-code",
        21: "Modal group violation",
        22: "Feed rate not set",
        23: "G-code command needs axis word",
        24: "Jog target exceeds machine travel",
        33: "Motion command would exceed soft limits",
    }
    
    # GRBL alarm codes
    ALARM_CODES = {
        1: "Hard limit triggered",
        2: "Soft limit exceeded",
        3: "Abort during cycle",
        4: "Probe fail",
        5: "Probe fail - no contact",
        6: "Homing fail - reset during cycle",
        7: "Homing fail - door opened",
        8: "Homing fail - pull off failed",
        9: "Homing fail - couldn't find limit switch",
    }
    
    def __init__(self, port: str, baud: int = 115200, timeout: float = 5.0):
        """
        Initialize GRBL controller.
        
        Args:
            port: Serial port (e.g., '/dev/ttyUSB0')
            baud: Baud rate (default 115200 for GRBL)
            timeout: Serial timeout in seconds
        """
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None
        self.char_counter = []
        self._lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """
        Connect to GRBL and perform wake-up sequence.
        
        Returns:
            bool: True if connected successfully
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Open serial connection in thread pool
            self.serial = await loop.run_in_executor(
                None,
                lambda: serial.Serial(self.port, self.baud, timeout=self.timeout)
            )
            
            # GRBL wake-up sequence
            self.serial.write(b"\r\n\r\n")
            await asyncio.sleep(2)
            self.serial.flushInput()
            
            # Read GRBL version string
            response = await loop.run_in_executor(None, self.serial.readline)
            version = response.decode().strip()
            logger.info(f"Connected to {version}")
            
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.serial.close)
            logger.info("Disconnected from plotter")
    
    async def send_command(self, command: str) -> str:
        """
        Send single command and wait for response.
        
        Args:
            command: G-code command
            
        Returns:
            str: Response from GRBL
            
        Raises:
            Exception: If command fails
        """
        async with self._lock:
            if not self.serial or not self.serial.is_open:
                raise Exception("Not connected")
            
            # Clean command
            command = command.strip()
            if not command:
                return "ok"
            
            loop = asyncio.get_event_loop()
            
            # Send command
            cmd_bytes = f"{command}\n".encode()
            await loop.run_in_executor(None, self.serial.write, cmd_bytes)
            logger.debug(f"→ {command}")
            
            # Wait for response
            while True:
                response = await loop.run_in_executor(None, self.serial.readline)
                response = response.decode().strip()
                
                if not response:
                    continue
                
                logger.debug(f"← {response}")
                
                if response == 'ok':
                    return response
                elif response.startswith('error:'):
                    error_code = int(response.split(':')[1])
                    error_msg = self.ERROR_CODES.get(error_code, "Unknown error")
                    raise Exception(f"GRBL Error {error_code}: {error_msg}")
                elif response.startswith('ALARM:'):
                    alarm_code = int(response.split(':')[1])
                    alarm_msg = self.ALARM_CODES.get(alarm_code, "Unknown alarm")
                    raise Exception(f"GRBL Alarm {alarm_code}: {alarm_msg}")
                elif response.startswith('<'):
                    # Status report, ignore
                    continue
                else:
                    return response
    
    async def stream_gcode_file(self, filepath: str, progress_callback=None) -> bool:
        """
        Stream G-code file using character-counting protocol.
        
        Args:
            filepath: Path to G-code file
            progress_callback: Optional callback(current, total)
            
        Returns:
            bool: True if streaming successful
        """
        async with self._lock:
            if not self.serial or not self.serial.is_open:
                raise Exception("Not connected")
            
            loop = asyncio.get_event_loop()
            
            # Read and clean G-code
            with open(filepath, 'r') as f:
                lines = []
                for line in f:
                    line = line.strip()
                    # Remove comments
                    if ';' in line:
                        line = line[:line.index(';')].strip()
                    if line and not line.startswith(';'):
                        lines.append(line)
            
            total_lines = len(lines)
            char_counter = []
            
            logger.info(f"Streaming {total_lines} lines")
            
            for i, line in enumerate(lines, 1):
                # Track character count
                char_counter.append(len(line) + 1)  # +1 for newline
                
                # Wait for buffer space
                while sum(char_counter) >= self.RX_BUFFER_SIZE - 1:
                    response = await loop.run_in_executor(None, self.serial.readline)
                    response = response.decode().strip()
                    
                    if response == 'ok':
                        char_counter.pop(0)
                    elif response.startswith('error:'):
                        char_counter.pop(0)
                        logger.error(f"Line {i} error: {response}")
                    elif response.startswith('ALARM:'):
                        logger.error(f"ALARM at line {i}: {response}")
                        return False
                
                # Send line
                cmd_bytes = f"{line}\n".encode()
                await loop.run_in_executor(None, self.serial.write, cmd_bytes)
                
                # Progress callback
                if progress_callback and i % 10 == 0:
                    await progress_callback(i, total_lines)
            
            # Wait for remaining responses
            while char_counter:
                response = await loop.run_in_executor(None, self.serial.readline)
                if response:
                    char_counter.pop(0)
            
            logger.info("Streaming complete")
            return True
    
    async def get_status(self) -> Dict[str, any]:
        """
        Query real-time status.
        
        Returns:
            dict: Parsed status information
        """
        if not self.serial or not self.serial.is_open:
            return {"state": "disconnected"}
        
        loop = asyncio.get_event_loop()
        
        # Send status query (doesn't interrupt command stream)
        await loop.run_in_executor(None, self.serial.write, b'?')
        
        # Read status response
        response = await loop.run_in_executor(None, self.serial.readline)
        status_string = response.decode().strip()
        
        return self._parse_status(status_string)
    
    def _parse_status(self, status_string: str) -> Dict[str, any]:
        """
        Parse GRBL 0.9 status string.
        
        Format: <Idle,MPos:0.000,0.000,0.000,WPos:0.000,0.000,0.000>
        """
        status_string = status_string.strip('<>\r\n')
        
        if not status_string:
            return {"state": "unknown"}
        
        parts = status_string.split(',')
        result = {"state": parts[0].lower()}
        
        i = 1
        while i < len(parts):
            if parts[i].startswith('MPos:'):
                coords = parts[i].split(':')[1]
                result['machine_position'] = {
                    'x': float(coords),
                    'y': float(parts[i+1]),
                    'z': float(parts[i+2])
                }
                i += 3
            elif parts[i].startswith('WPos:'):
                coords = parts[i].split(':')[1]
                result['work_position'] = {
                    'x': float(coords),
                    'y': float(parts[i+1]),
                    'z': float(parts[i+2])
                }
                i += 3
            else:
                i += 1
        
        return result
    
    async def reset(self) -> None:
        """Soft reset (Ctrl-X)."""
        if self.serial and self.serial.is_open:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.serial.write, b'\x18')
            await asyncio.sleep(2)
            logger.info("GRBL reset")
    
    async def unlock(self) -> None:
        """Unlock from alarm state."""
        await self.send_command('$X')
        logger.info("Alarm unlocked")
