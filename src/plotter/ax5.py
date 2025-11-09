"""
AX5 Plotter implementation with CoreXY kinematics and GRBL 0.9.
"""
import asyncio
import logging
from typing import Dict, Optional, Tuple
import yaml

from .interface import (
    PlotterInterface, PlotterState, PlotterError,
    PlotterConnectionError, PlotterAlarmError
)
from .grbl import GRBLController

logger = logging.getLogger(__name__)


class AX5Plotter(PlotterInterface):
    """AX5 plotter with CoreXY kinematics and servo pen control."""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Initialize AX5 plotter.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        plotter_config = self.config['plotter']
        servo_config = self.config['servo']
        speed_config = self.config['speeds']
        
        # Initialize GRBL controller
        self.grbl = GRBLController(
            port=plotter_config['port'],
            baud=plotter_config['baud'],
            timeout=plotter_config['timeout']
        )
        
        # Store settings
        self.width = plotter_config['dimensions']['width']
        self.height = plotter_config['dimensions']['height']
        self.pen_up_cmd = servo_config['pen_up_command']
        self.pen_down_cmd = servo_config['pen_down_command']
        self.dwell_time = servo_config['dwell_time']
        self.travel_speed = speed_config['travel']
        self.draw_speed = speed_config['draw']
        
        self._connected = False
        self._homed = False
    
    async def connect(self) -> bool:
        """Connect to AX5 plotter."""
        try:
            success = await self.grbl.connect()
            if success:
                await self._configure_grbl()
                self._connected = True
                logger.info("AX5 plotter connected and configured")
            return success
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise PlotterConnectionError(str(e))
    
    async def disconnect(self) -> None:
        """Disconnect from plotter."""
        await self.grbl.disconnect()
        self._connected = False
        logger.info("AX5 plotter disconnected")
    
    async def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected
    
    async def _configure_grbl(self) -> None:
        """Configure GRBL settings for AX5."""
        settings = self.config['plotter']['grbl']
        
        logger.info("Configuring GRBL settings...")
        
        grbl_commands = {
            '$32': str(settings['laser_mode']),  # Laser mode OFF
            '$110': str(settings['max_rate_x']),
            '$111': str(settings['max_rate_y']),
            '$112': str(settings['max_rate_z']),
            '$120': str(settings['acceleration_x']),
            '$121': str(settings['acceleration_y']),
            '$130': str(settings['max_travel_x']),
            '$131': str(settings['max_travel_y']),
            '$10': str(settings['status_report']),
        }
        
        for cmd, value in grbl_commands.items():
            try:
                await self.grbl.send_command(f"{cmd}={value}")
            except Exception as e:
                logger.warning(f"Failed to set {cmd}: {e}")
    
    async def home(self) -> bool:
        """Execute homing cycle."""
        try:
            logger.info("Starting homing cycle...")
            await self.grbl.send_command('$H')
            
            # Wait for homing to complete
            while True:
                status = await self.get_status()
                if status['state'] == PlotterState.IDLE.value:
                    self._homed = True
                    logger.info("Homing complete")
                    return True
                elif status['state'] == PlotterState.ALARM.value:
                    raise PlotterAlarmError(0, "Homing failed")
                
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Homing failed: {e}")
            return False
    
    async def move_to(self, x: float, y: float, speed: Optional[int] = None) -> None:
        """
        Move to absolute position.
        
        Args:
            x: X coordinate in mm
            y: Y coordinate in mm  
            speed: Feed rate in mm/min (default: travel speed)
        """
        if not self._connected:
            raise PlotterError("Not connected")
        
        speed = speed or self.travel_speed
        
        # Validate coordinates
        if not (0 <= x <= self.width):
            raise PlotterError(f"X coordinate {x} out of bounds (0-{self.width})")
        if not (0 <= y <= self.height):
            raise PlotterError(f"Y coordinate {y} out of bounds (0-{self.height})")
        
        command = f"G0 X{x:.3f} Y{y:.3f} F{speed}"
        await self.grbl.send_command(command)
        logger.debug(f"Moved to X{x:.3f} Y{y:.3f}")
    
    async def pen_control(self, down: bool) -> None:
        """
        Control pen up/down.
        
        Args:
            down: True for pen down, False for pen up
        """
        if not self._connected:
            raise PlotterError("Not connected")
        
        command = self.pen_down_cmd if down else self.pen_up_cmd
        await self.grbl.send_command(command)
        
        # Add dwell for servo settling
        await self.grbl.send_command(f"G4 P{self.dwell_time}")
        
        logger.debug(f"Pen {'down' if down else 'up'}")
    
    async def send_command(self, command: str) -> str:
        """Send raw G-code command."""
        if not self._connected:
            raise PlotterError("Not connected")
        
        return await self.grbl.send_command(command)
    
    async def get_status(self) -> Dict[str, any]:
        """Get current plotter status."""
        if not self._connected:
            return {
                "state": PlotterState.DISCONNECTED.value,
                "position": {"x": 0, "y": 0, "z": 0},
                "machine_position": {"x": 0, "y": 0, "z": 0}
            }
        
        grbl_status = await self.grbl.get_status()
        
        # Convert GRBL state to PlotterState
        state_map = {
            "idle": PlotterState.IDLE.value,
            "run": PlotterState.RUNNING.value,
            "home": PlotterState.HOMING.value,
            "alarm": PlotterState.ALARM.value,
            "unknown": PlotterState.ERROR.value,
        }
        
        return {
            "state": state_map.get(grbl_status.get('state', 'unknown'), PlotterState.ERROR.value),
            "position": grbl_status.get('work_position', {"x": 0, "y": 0, "z": 0}),
            "machine_position": grbl_status.get('machine_position', {"x": 0, "y": 0, "z": 0}),
            "homed": self._homed
        }
    
    async def stream_gcode(self, gcode: str, progress_callback=None) -> bool:
        """
        Stream G-code file to plotter.
        
        Args:
            gcode: Path to G-code file
            progress_callback: Optional callback(current, total)
            
        Returns:
            bool: True if successful
        """
        if not self._connected:
            raise PlotterError("Not connected")
        
        logger.info(f"Starting G-code stream: {gcode}")
        
        try:
            success = await self.grbl.stream_gcode_file(gcode, progress_callback)
            
            if success:
                logger.info("G-code streaming complete")
            else:
                logger.error("G-code streaming failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise PlotterError(f"Streaming failed: {e}")
    
    async def emergency_stop(self) -> None:
        """Execute emergency stop."""
        if self._connected:
            await self.grbl.reset()
            logger.warning("Emergency stop executed")
    
    async def reset(self) -> None:
        """Soft reset plotter."""
        if self._connected:
            await self.grbl.reset()
            self._homed = False
            logger.info("Plotter reset")
    
    async def unlock(self) -> None:
        """Unlock from alarm state."""
        if self._connected:
            await self.grbl.unlock()
            logger.info("Plotter unlocked")
    
    def get_dimensions(self) -> Tuple[float, float]:
        """Get plotter dimensions in mm."""
        return (self.width, self.height)
    
    async def set_pen_profile(self, profile_name: str) -> None:
        """
        Set pen type profile.
        
        Args:
            profile_name: Profile name from config (marker, ballpoint, fountain)
        """
        profiles = self.config['servo']['profiles']
        
        if profile_name not in profiles:
            raise PlotterError(f"Unknown pen profile: {profile_name}")
        
        profile = profiles[profile_name]
        self.dwell_time = profile['dwell']
        self.draw_speed = profile['speed']
        
        logger.info(f"Pen profile set to: {profile_name}")


# Convenience function for initialization
async def create_ax5_plotter(config_path: str = "config/settings.yaml") -> AX5Plotter:
    """
    Create and connect to AX5 plotter.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        AX5Plotter: Connected plotter instance
    """
    plotter = AX5Plotter(config_path)
    await plotter.connect()
    return plotter
