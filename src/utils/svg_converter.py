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
        optimize: bool = False  # Changed to False by default - vpype not always available
    ) -> str:
        """
        Convert SVG to G-code.
        
        Args:
            svg_file: Path to input SVG file
            output_file: Optional output G-code path (auto-generated if None)
            pen_profile: Pen type profile name
            optimize: Whether to apply path optimization (requires vpype)
            
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
        
        # Try vpype first if optimize is requested, but fall back to basic if it fails
        if optimize:
            try:
                return self._convert_with_vpype(svg_file, output_file, pen_profile)
            except Exception as e:
                logger.warning(f"vpype optimization failed ({e}), using basic conversion")
                return self._convert_basic(svg_file, output_file, pen_profile)
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
            
            # Layout and scale - use A5 landscape with centered alignment and margins
            cmd.extend([
                "layout",
                "--landscape",
                f"--fit-to-margins={margin}mm",
                "a5",
                # Translate to center the drawing properly on the page
                # A5 landscape is 210mm x 148mm, we want 210mm x 150mm effectively
                "translate", f"{margin}mm", f"{margin}mm"
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

            # Center the G-code output on the page
            self._center_gcode(output_file, width, height)

            return output_file
            
        except FileNotFoundError:
            logger.warning("vpype not found, falling back to basic conversion")
            return self._convert_basic(svg_file, output_file, pen_profile)
        except subprocess.CalledProcessError as e:
            logger.warning(f"vpype failed: {e}, falling back to basic conversion")
            return self._convert_basic(svg_file, output_file, pen_profile)
        except Exception as e:
            logger.error(f"vpype conversion failed: {e}, falling back to basic conversion")
            return self._convert_basic(svg_file, output_file, pen_profile)
    
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
            # Normalize resulting G-code to ensure compatibility with AX5
            self._normalize_gcode(output_file, pen_profile)
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
    
    def _center_gcode(self, gcode_file: str, page_width: float, page_height: float) -> None:
        """
        Center the G-code drawing on the page by calculating bounds and adding offset.
        
        Args:
            gcode_file: G-code file to center
            page_width: Target page width in mm
            page_height: Target page height in mm
        """
        import re
        
        # Read G-code and find bounds
        with open(gcode_file, 'r') as f:
            lines = f.readlines()
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for line in lines:
            x_match = re.search(r'X([\d.]+)', line)
            y_match = re.search(r'Y([\d.]+)', line)
            if x_match:
                x = float(x_match.group(1))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
            if y_match:
                y = float(y_match.group(1))
                min_y = min(min_y, y)
                max_y = max(max_y, y)
        
        # Calculate centering offset
        drawing_width = max_x - min_x
        drawing_height = max_y - min_y
        offset_x = (page_width - drawing_width) / 2 - min_x
        offset_y = (page_height - drawing_height) / 2 - min_y
        
        logger.info(f"Centering: drawing={drawing_width:.1f}x{drawing_height:.1f}mm, offset=({offset_x:.1f}, {offset_y:.1f})mm")
        
        # Apply offset to all coordinates
        centered_lines = []
        for line in lines:
            new_line = line
            x_match = re.search(r'X([\d.]+)', line)
            y_match = re.search(r'Y([\d.]+)', line)
            
            if x_match:
                old_x = float(x_match.group(1))
                new_x = old_x + offset_x
                new_line = new_line.replace(f'X{x_match.group(1)}', f'X{new_x:.4f}')
            
            if y_match:
                old_y = float(y_match.group(1))
                new_y = old_y + offset_y
                new_line = new_line.replace(f'Y{y_match.group(1)}', f'Y{new_y:.4f}')
            
            centered_lines.append(new_line)
        
        # Write back centered G-code
        with open(gcode_file, 'w') as f:
            f.writelines(centered_lines)
        
        logger.info(f"G-code centered on {page_width}x{page_height}mm page")
    
    def _normalize_gcode(self, gcode_file: str, pen_profile: str) -> None:
        """
        Ensure G-code conforms to a minimal AX5-safe structure:
        - Add a standard header if missing
```
        - Ensure pen up/down dwells use the profile dwell time
        - Ensure movement commands include sensible feed rates
        - Append a footer that raises the pen and homes X/Y

        This is intentionally conservative to make the basic converter
        output safe for the AX5 when vpype is not available.
        """
        profile = self.servo_config['profiles'].get(
            pen_profile,
            self.servo_config['profiles']['ballpoint']
        )

        pen_up = self.servo_config.get('pen_up_command', 'M5')
        pen_down = self.servo_config.get('pen_down_command', 'M3')
        dwell = profile.get('dwell', self.servo_config.get('dwell_time', 0.5))
        travel_f = self.speed_config.get('travel', 1500)
        draw_f = profile.get('speed', self.speed_config.get('draw', 800))

        with open(gcode_file, 'r') as f:
            raw_lines = [ln.rstrip('\n') for ln in f.readlines()]

        # Filter out empty lines for processing
        lines = [ln for ln in raw_lines if ln.strip()]

        new_lines = []
        
        # Ensure proper header is always present
        has_header = any('G21' in ln and 'G90' in ln for ln in lines[:5])
        if not has_header:
            new_lines.extend([
                'G21 G90 G17',
                f"{pen_up}",
                f"G4 P{dwell}",
            ])

        pen_is_down = False
        for ln in lines:
            upper = ln.strip().upper()
            
            # Skip if this looks like our header (we already added it)
            if not has_header and ('G21' in upper or 'G90' in upper):
                continue

            # Normalize dwell lines
            if upper.startswith('G4'):
                new_lines.append(f"G4 P{dwell}")
                continue

            # Track pen state and ensure dwell after state changes
            if pen_down in ln:
                pen_is_down = True
                new_lines.append(pen_down)
                new_lines.append(f"G4 P{dwell}")
                continue
            if pen_up in ln:
                pen_is_down = False
                new_lines.append(pen_up)
                new_lines.append(f"G4 P{dwell}")
                continue

            # Movement commands: ensure feedrates
            if upper.startswith('G0') or upper.startswith('G1'):
                if 'F' not in upper:
                    fval = draw_f if pen_is_down else travel_f
                    new_lines.append(f"{ln} F{int(fval)}")
                else:
                    new_lines.append(ln)
                continue

            # Keep other commands as-is (but skip M2 since we add footer)
            if upper != 'M2' and upper != 'M30':
                new_lines.append(ln)

        # Always ensure a proper footer
        has_m2 = any('M2' in ln.upper() or 'M30' in ln.upper() for ln in new_lines[-3:])
        if not has_m2:
            # Make sure pen is up and we return home
            new_lines.append(pen_up)
            new_lines.append(f"G4 P{dwell}")
            new_lines.append(f"G0 X0 Y0 F{int(travel_f)}")
            new_lines.append('M2')

        # Write back
        with open(gcode_file, 'w') as f:
            f.write('\n'.join(new_lines) + '\n')

        logger.info(f"Normalized G-code: {gcode_file}")

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
    
    # Build profile with single braces for vpype template substitution
    profile = f"""[gwrite.ax5_custom]
unit = "mm"
vertical_flip = true

document_start = \"\"\"
G21 G90 G17
{servo_config['pen_up_command']}
G4 P{servo_config['dwell_time']}
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
    
    with open(vpype_config_path, 'w') as f:
        f.write(profile)
    
    logger.info(f"vpype profile created at {vpype_config_path}")
