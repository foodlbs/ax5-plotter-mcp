"""
SVG to G-code conversion with path optimization.
"""
import os
import subprocess
import logging
from typing import Optional, Tuple
import yaml

logger = logging.getLogger(__name__)


class SVGConverter:
    """Convert SVG files to optimized G-code for AX5 plotter."""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Initialize converter.
        
        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.plotter_config = self.config['plotter']
        self.servo_config = self.config['servo']
        self.speed_config = self.config['speeds']
        self.opt_config = self.config['optimization']
    
    def convert(
        self,
        svg_file: str,
        output_file: Optional[str] = None,
        pen_profile: str = "ballpoint",
        optimize: bool = True
    ) -> str:
        """
        Convert SVG to G-code.
        
        Args:
            svg_file: Path to input SVG file
            output_file: Optional output G-code path (auto-generated if None)
            pen_profile: Pen type profile name
            optimize: Whether to apply path optimization
            
        Returns:
            str: Path to generated G-code file
        """
        if not os.path.exists(svg_file):
            raise FileNotFoundError(f"SVG file not found: {svg_file}")
        
        # Generate output filename
        if output_file is None:
            base_name = os.path.splitext(os.path.basename(svg_file))[0]
            output_dir = self.config['api']['output_dir']
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{base_name}.gcode")
        
        logger.info(f"Converting {svg_file} to {output_file}")
        
        if optimize:
            return self._convert_with_vpype(svg_file, output_file, pen_profile)
        else:
            return self._convert_basic(svg_file, output_file, pen_profile)
    
    def _convert_with_vpype(
        self,
        svg_file: str,
        output_file: str,
        pen_profile: str
    ) -> str:
        """
        Convert using vpype with optimization pipeline.
        
        Args:
            svg_file: Input SVG path
            output_file: Output G-code path
            pen_profile: Pen profile name
            
        Returns:
            str: Output file path
        """
        try:
            # Build vpype command
            width = self.plotter_config['dimensions']['width']
            height = self.plotter_config['dimensions']['height']
            margin = self.plotter_config['dimensions']['margin']
            
            merge_tol = self.opt_config['merge_tolerance']
            simplify_tol = self.opt_config['simplify_tolerance']
            
            cmd = [
                "vpype",
                "read", svg_file,
            ]
            
            # Optimization steps
            if self.opt_config['merge_tolerance']:
                cmd.extend(["linemerge", f"--tolerance={merge_tol}mm"])
            
            if self.opt_config['use_line_sort']:
                cmd.extend(["linesort", "--two-opt"])
            
            if self.opt_config['reloop']:
                cmd.append("reloop")
            
            if self.opt_config['simplify_tolerance']:
                cmd.extend(["linesimplify", f"--tolerance={simplify_tol}mm"])
            
            # Layout and scaling
            cmd.extend([
                "layout",
                f"--fit-to-margins={margin}mm",
                f"{width}x{height}mm"
            ])
            
            # G-code output
            cmd.extend([
                "gwrite",
                "--profile=ax5_custom",
                output_file
            ])
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            # Run vpype
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.returncode != 0:
                raise Exception(f"vpype failed: {result.stderr}")
            
            logger.info("vpype conversion successful")
            
            # Post-process G-code for pen profile
            self._apply_pen_profile(output_file, pen_profile)
            
            return output_file
            
        except FileNotFoundError:
            logger.warning("vpype not found, falling back to basic conversion")
            return self._convert_basic(svg_file, output_file, pen_profile)
        except Exception as e:
            logger.error(f"vpype conversion failed: {e}")
            raise
    
    def _convert_basic(
        self,
        svg_file: str,
        output_file: str,
        pen_profile: str
    ) -> str:
        """
        Basic conversion using svg-to-gcode library.
        
        Args:
            svg_file: Input SVG path
            output_file: Output G-code path
            pen_profile: Pen profile name
            
        Returns:
            str: Output file path
        """
        try:
            from svg_to_gcode.svg_parser import parse_file
            from svg_to_gcode.compiler import Compiler, interfaces
            
            # Get pen profile settings
            profile = self.servo_config['profiles'].get(
                pen_profile,
                self.servo_config['profiles']['ballpoint']
            )
            
            # Create custom interface for AX5
            class AX5Interface(interfaces.Gcode):
                def __init__(self, servo_config, speed_config):
                    super().__init__()
                    self.servo_config = servo_config
                    self.speed_config = speed_config
                
                def header(self):
                    return """G21 G90 G17
M3 S1000
G4 P0.5
"""
                
                def laser_off(self):
                    return f"{self.servo_config['pen_up_command']}\nG4 P{self.servo_config['dwell_time']}\n"
                
                def set_laser_power(self, power):
                    return f"{self.servo_config['pen_down_command']}\nG4 P{self.servo_config['dwell_time']}\n"
                
                def footer(self):
                    return f"""{self.servo_config['pen_up_command']}
G0 X0 Y0
M2
"""
            
            # Setup compiler
            compiler = Compiler(
                lambda: AX5Interface(self.servo_config, self.speed_config),
                movement_speed=self.speed_config['travel'],
                cutting_speed=profile['speed'],
                pass_depth=0
            )
            
            # Parse and compile
            curves = parse_file(svg_file)
            compiler.append_curves(curves)
            compiler.compile_to_file(output_file)
            
            logger.info("Basic SVG conversion successful")
            return output_file
            
        except ImportError:
            raise Exception("svg-to-gcode library not installed. Run: pip install svg-to-gcode")
        except Exception as e:
            logger.error(f"Basic conversion failed: {e}")
            raise
    
    def _apply_pen_profile(self, gcode_file: str, pen_profile: str) -> None:
        """
        Post-process G-code to apply pen profile settings.
        
        Args:
            gcode_file: G-code file to modify
            pen_profile: Pen profile name
        """
        profile = self.servo_config['profiles'].get(
            pen_profile,
            self.servo_config['profiles']['ballpoint']
        )
        
        # Read G-code
        with open(gcode_file, 'r') as f:
            lines = f.readlines()
        
        # Modify speeds and dwells
        modified = []
        for line in lines:
            # Replace feed rates
            if 'F' in line and any(c in line for c in 'GXY'):
                # Determine if this is a travel or draw move
                # This is simplified - in real implementation, track pen state
                modified.append(line)
            # Replace dwell times
            elif line.startswith('G4 P'):
                modified.append(f"G4 P{profile['dwell']}\n")
            else:
                modified.append(line)
        
        # Write back
        with open(gcode_file, 'w') as f:
            f.writelines(modified)
        
        logger.debug(f"Applied pen profile: {pen_profile}")
    
    def estimate_time(self, gcode_file: str) -> float:
        """
        Estimate plotting time in seconds.
        
        Args:
            gcode_file: G-code file to analyze
            
        Returns:
            float: Estimated time in seconds
        """
        total_time = 0
        current_pos = (0, 0)
        pen_down = False
        
        with open(gcode_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Track pen state
                if self.servo_config['pen_down_command'] in line:
                    pen_down = True
                    total_time += self.servo_config['dwell_time']
                elif self.servo_config['pen_up_command'] in line:
                    pen_down = False
                    total_time += self.servo_config['dwell_time']
                
                # Calculate move time
                if line.startswith('G0') or line.startswith('G1'):
                    x, y = current_pos
                    
                    if 'X' in line:
                        x = float(line.split('X')[1].split()[0])
                    if 'Y' in line:
                        y = float(line.split('Y')[1].split()[0])
                    
                    distance = ((x - current_pos[0])**2 + (y - current_pos[1])**2)**0.5
                    
                    speed = self.speed_config['draw'] if pen_down else self.speed_config['travel']
                    time = (distance / speed) * 60  # Convert mm/min to seconds
                    
                    total_time += time
                    current_pos = (x, y)
        
        return total_time


def create_vpype_profile(config_path: str = "config/settings.yaml") -> None:
    """
    Create vpype-gcode profile configuration.
    
    Args:
        config_path: Path to settings file
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    servo_config = config['servo']
    
    profile = f"""
[gwrite.ax5_custom]
unit = "mm"
vertical_flip = true

document_start = \"\"\"
G21 G90 G17
M3 S1000
G4 P0.5
\"\"\"

segment_first = \"\"\"
{servo_config['pen_up_command']}
G4 P{servo_config['dwell_time']}
G0 X{{x:.4f}} Y{{y:.4f}}
{servo_config['pen_down_command']}
G4 P{servo_config['dwell_time']}
\"\"\"

segment = "G1 X{{x:.4f}} Y{{y:.4f}}\\n"

line_end = \"\"\"
{servo_config['pen_up_command']}
\"\"\"

document_end = \"\"\"
{servo_config['pen_up_command']}
G0 X0 Y0
M2
\"\"\"
"""
    
    # Write to ~/.vpype.toml
    vpype_config_path = os.path.expanduser("~/.vpype.toml")
    
    with open(vpype_config_path, 'a') as f:
        f.write(profile)
    
    logger.info(f"vpype profile created at {vpype_config_path}")
