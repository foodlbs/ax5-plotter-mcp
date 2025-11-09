"""
Abstract plotter interface for hardware abstraction.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from enum import Enum


class PlotterState(Enum):
    """Plotter state enumeration."""
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    HOMING = "homing"
    RUNNING = "running"
    ALARM = "alarm"
    ERROR = "error"


class PlotterInterface(ABC):
    """Abstract interface for plotter control."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the plotter hardware.
        
        Returns:
            bool: True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from plotter hardware."""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if plotter is connected."""
        pass
    
    @abstractmethod
    async def home(self) -> bool:
        """
        Execute homing cycle.
        
        Returns:
            bool: True if homing successful
        """
        pass
    
    @abstractmethod
    async def move_to(self, x: float, y: float, speed: Optional[int] = None) -> None:
        """
        Move to absolute position.
        
        Args:
            x: X coordinate in mm
            y: Y coordinate in mm
            speed: Optional feed rate in mm/min
        """
        pass
    
    @abstractmethod
    async def pen_control(self, down: bool) -> None:
        """
        Control pen up/down.
        
        Args:
            down: True for pen down, False for pen up
        """
        pass
    
    @abstractmethod
    async def send_command(self, command: str) -> str:
        """
        Send raw command to plotter.
        
        Args:
            command: Command string
            
        Returns:
            str: Response from plotter
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, any]:
        """
        Get current plotter status.
        
        Returns:
            dict: Status dictionary with keys:
                - state: PlotterState
                - position: Dict[str, float] with x, y, z
                - machine_position: Dict[str, float]
                - error: Optional error message
        """
        pass
    
    @abstractmethod
    async def stream_gcode(self, gcode: str, progress_callback=None) -> bool:
        """
        Stream G-code to plotter.
        
        Args:
            gcode: G-code string or path to file
            progress_callback: Optional callback(current, total) for progress
            
        Returns:
            bool: True if streaming successful
        """
        pass
    
    @abstractmethod
    async def emergency_stop(self) -> None:
        """Execute emergency stop."""
        pass
    
    @abstractmethod
    async def reset(self) -> None:
        """Soft reset plotter."""
        pass
    
    @abstractmethod
    async def unlock(self) -> None:
        """Unlock from alarm state."""
        pass
    
    @abstractmethod
    def get_dimensions(self) -> Tuple[float, float]:
        """
        Get plotter dimensions.
        
        Returns:
            Tuple[float, float]: (width, height) in mm
        """
        pass


class PlotterError(Exception):
    """Base exception for plotter errors."""
    pass


class PlotterConnectionError(PlotterError):
    """Raised when connection fails."""
    pass


class PlotterAlarmError(PlotterError):
    """Raised when plotter enters alarm state."""
    
    def __init__(self, alarm_code: int, message: str):
        self.alarm_code = alarm_code
        super().__init__(f"ALARM {alarm_code}: {message}")


class PlotterCommandError(PlotterError):
    """Raised when command execution fails."""
    
    def __init__(self, command: str, error_code: int, message: str):
        self.command = command
        self.error_code = error_code
        super().__init__(f"Command '{command}' failed (error {error_code}): {message}")
