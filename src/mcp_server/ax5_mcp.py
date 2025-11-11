"""
Model Context Protocol (MCP) server for AX5 plotter control.

This server enables AI-assisted plotter control through standardized
LLM integration via the MCP protocol.
"""
import os
import sys
import logging
from typing import Optional
import asyncio

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
import yaml
from redis import Redis
from rq import Queue
from rq.job import Job

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.plotter.ax5 import AX5Plotter
from src.workers.plot_worker import process_plot_job

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration with error handling
try:
    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    logger.error("Configuration file not found: config/settings.yaml")
    logger.error("Please copy config/settings.example.yaml to config/settings.yaml")
    raise
except yaml.YAMLError as e:
    logger.error(f"Error parsing configuration file: {e}")
    raise

# Initialize MCP server
mcp = FastMCP("AX5 Plotter Control")


# Response Models
class PlotterStatusResponse(BaseModel):
    """Plotter status response."""
    state: str = Field(description="Current state: idle, plotting, error")
    position: dict = Field(description="Current X,Y coordinates in mm")
    machine_position: dict = Field(description="Machine coordinates")
    homed: bool = Field(description="Whether plotter has been homed")
    connected: bool = Field(description="Connection status")


class PlotJobResponse(BaseModel):
    """Plot job submission response."""
    job_id: str = Field(description="Unique job identifier")
    status: str = Field(description="Job status: queued, started, finished, failed")
    queue_position: int = Field(description="Position in queue")
    message: str = Field(description="Human-readable message")


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    progress: float = Field(description="Progress percentage (0-100)")
    stage: Optional[str] = Field(description="Current stage: converting, connecting, plotting")
    current_command: Optional[int] = None
    total_commands: Optional[int] = None
    estimated_time: Optional[float] = Field(description="Estimated time in seconds")
    error: Optional[str] = None


# Initialize Redis and RQ
redis_conn = Redis(
    host=config['redis']['host'],
    port=config['redis']['port'],
    db=config['redis']['db'],
    decode_responses=True
)

high_queue = Queue('high', connection=redis_conn)
normal_queue = Queue('normal', connection=redis_conn)
low_queue = Queue('low', connection=redis_conn)


# MCP Tools

@mcp.tool()
async def get_plotter_status(ctx: Context) -> PlotterStatusResponse:
    """
    Get current plotter status and position.
    
    Returns the plotter's current state (idle, plotting, error), position,
    homing status, and connection state.
    """
    await ctx.info("Checking plotter status...")
    
    plotter = AX5Plotter()
    
    try:
        await plotter.connect()
        status = await plotter.get_status()
        connected = await plotter.is_connected()
        
        await ctx.info(f"Plotter is {status['state']}")
        
        return PlotterStatusResponse(
            state=status['state'],
            position=status['position'],
            machine_position=status['machine_position'],
            homed=status.get('homed', False),
            connected=connected
        )
        
    except Exception as e:
        await ctx.error(f"Failed to get status: {e}")
        return PlotterStatusResponse(
            state="error",
            position={"x": 0, "y": 0, "z": 0},
            machine_position={"x": 0, "y": 0, "z": 0},
            homed=False,
            connected=False
        )
    finally:
        await plotter.disconnect()


@mcp.tool()
async def submit_plot_job(
    svg_file: str,
    priority: str = "normal",
    pen_type: str = "ballpoint",
    optimize: bool = True,
    ctx: Context = None
) -> PlotJobResponse:
    """
    Submit SVG file for plotting.
    
    Args:
        svg_file: Path to SVG file to plot
        priority: Job priority - "high", "normal", or "low" (default: normal)
        pen_type: Pen type profile - "marker", "ballpoint", or "fountain" (default: ballpoint)
        optimize: Whether to apply path optimization (default: true)
    
    Returns job ID and status. Use get_job_status() to monitor progress.
    """
    # Validate file
    if not os.path.exists(svg_file):
        await ctx.error(f"File not found: {svg_file}")
        raise FileNotFoundError(f"SVG file not found: {svg_file}")
    
    if not svg_file.lower().endswith('.svg'):
        await ctx.error("File must be SVG format")
        raise ValueError("File must be SVG format")
    
    await ctx.info(f"Submitting plot job for {svg_file}")
    
    # Select queue
    if priority == "high":
        queue = high_queue
    elif priority == "low":
        queue = low_queue
    else:
        queue = normal_queue
    
    # Enqueue job
    job = queue.enqueue(
        process_plot_job,
        svg_file,
        options={
            'pen_type': pen_type,
            'optimize': optimize
        },
        timeout=config['queue']['default_timeout']
    )
    
    await ctx.info(f"Job {job.id} queued (position {queue.count})")
    
    return PlotJobResponse(
        job_id=job.id,
        status="queued",
        queue_position=queue.count,
        message=f"Plot job queued. Use get_job_status('{job.id}') to monitor progress."
    )


@mcp.tool()
async def get_job_status(
    job_id: str,
    ctx: Context = None
) -> JobStatusResponse:
    """
    Get status of a specific plot job.
    
    Args:
        job_id: Job identifier returned from submit_plot_job()
    
    Returns current job status, progress, and any errors.
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        status = job.get_status()
        progress = job.meta.get('progress', 0)
        
        if status == "finished":
            await ctx.info(f"Job {job_id} completed successfully")
        elif status == "failed":
            await ctx.error(f"Job {job_id} failed: {job.meta.get('error')}")
        else:
            await ctx.info(f"Job {job_id} is {status} ({progress:.1f}% complete)")
        
        return JobStatusResponse(
            job_id=job_id,
            status=status,
            progress=progress,
            stage=job.meta.get('stage'),
            current_command=job.meta.get('current_command'),
            total_commands=job.meta.get('total_commands'),
            estimated_time=job.meta.get('estimated_time'),
            error=job.meta.get('error') if job.is_failed else None
        )
        
    except Exception as e:
        await ctx.error(f"Job not found: {e}")
        raise FileNotFoundError(f"Job {job_id} not found")


@mcp.tool()
async def cancel_job(
    job_id: str,
    ctx: Context = None
) -> dict:
    """
    Cancel a running or queued plot job.
    
    Args:
        job_id: Job identifier to cancel
    
    Returns cancellation status.
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        if job.is_started or job.is_queued:
            job.cancel()
            await ctx.info(f"Job {job_id} cancelled")
            return {
                "status": "cancelled",
                "job_id": job_id,
                "message": f"Job {job_id} has been cancelled"
            }
        else:
            await ctx.info(f"Job {job_id} cannot be cancelled (status: {job.get_status()})")
            return {
                "status": "cannot_cancel",
                "job_id": job_id,
                "reason": f"Job is {job.get_status()}"
            }
            
    except Exception as e:
        await ctx.error(f"Failed to cancel job: {e}")
        raise


@mcp.tool()
async def home_plotter(ctx: Context) -> dict:
    """
    Execute plotter homing cycle.
    
    Moves the plotter to its home position (0,0) and establishes
    a reference point for accurate plotting.
    """
    await ctx.info("Starting homing cycle...")
    
    plotter = AX5Plotter()
    
    try:
        await plotter.connect()
        success = await plotter.home()
        
        if success:
            await ctx.info("Homing complete")
            return {
                "status": "success",
                "message": "Plotter homed successfully"
            }
        else:
            await ctx.error("Homing failed")
            return {
                "status": "error",
                "message": "Homing cycle failed"
            }
            
    except Exception as e:
        await ctx.error(f"Homing error: {e}")
        raise
    finally:
        await plotter.disconnect()


@mcp.tool()
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 10,
    ctx: Context = None
) -> list:
    """
    List plot jobs with optional status filter.
    
    Args:
        status: Optional filter - "queued", "started", "finished", or "failed"
        limit: Maximum number of jobs to return (default: 10)
    
    Returns list of jobs with their status and progress.
    """
    from rq.registry import (
        StartedJobRegistry,
        FinishedJobRegistry,
        FailedJobRegistry
    )
    
    jobs = []
    
    registries = {
        'started': StartedJobRegistry(queue=normal_queue),
        'finished': FinishedJobRegistry(queue=normal_queue),
        'failed': FailedJobRegistry(queue=normal_queue),
    }
    
    for reg_name, registry in registries.items():
        if status is None or status == reg_name:
            for job_id in registry.get_job_ids()[:limit]:
                try:
                    job = Job.fetch(job_id, connection=redis_conn)
                    jobs.append({
                        "job_id": job.id,
                        "status": job.get_status(),
                        "progress": job.meta.get('progress', 0),
                        "stage": job.meta.get('stage')
                    })
                except:
                    pass
    
    await ctx.info(f"Found {len(jobs)} jobs")
    return jobs


@mcp.tool()
async def move_to_position(
    x: float,
    y: float,
    ctx: Context = None
) -> dict:
    """
    Move plotter to specific X,Y position.
    
    Args:
        x: X coordinate in millimeters (0-210 for A5)
        y: Y coordinate in millimeters (0-150 for A5)
    
    Useful for testing positioning or manual control.
    """
    plotter = AX5Plotter()
    
    try:
        await plotter.connect()
        
        # Validate coordinates
        width, height = plotter.get_dimensions()
        
        if not (0 <= x <= width):
            await ctx.error(f"X coordinate {x} out of bounds (0-{width})")
            raise ValueError(f"X must be between 0 and {width}")
        
        if not (0 <= y <= height):
            await ctx.error(f"Y coordinate {y} out of bounds (0-{height})")
            raise ValueError(f"Y must be between 0 and {height}")
        
        await ctx.info(f"Moving to X{x:.1f} Y{y:.1f}")
        await plotter.move_to(x, y)
        
        return {
            "status": "success",
            "position": {"x": x, "y": y},
            "message": f"Moved to X{x:.1f} Y{y:.1f}"
        }
        
    except Exception as e:
        await ctx.error(f"Move failed: {e}")
        raise
    finally:
        await plotter.disconnect()


@mcp.tool()
async def control_pen(
    down: bool,
    ctx: Context = None
) -> dict:
    """
    Manual pen control for testing.
    
    Args:
        down: True to lower pen, False to raise pen
    
    Useful for testing servo operation.
    """
    plotter = AX5Plotter()
    
    try:
        await plotter.connect()
        await plotter.pen_control(down)
        
        await ctx.info(f"Pen {'lowered' if down else 'raised'}")
        
        return {
            "status": "success",
            "pen": "down" if down else "up"
        }
        
    except Exception as e:
        await ctx.error(f"Pen control failed: {e}")
        raise
    finally:
        await plotter.disconnect()


# MCP Resources

@mcp.resource("plotter://status")
def get_plotter_resource(ctx: Context) -> str:
    """
    Real-time plotter status resource.
    
    Provides current plotter state as a resource.
    """
    import json
    
    # This is a synchronous wrapper - in production, use async properly
    plotter = AX5Plotter()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(plotter.connect())
        status = loop.run_until_complete(plotter.get_status())
        
        return json.dumps(status, indent=2)
    finally:
        loop.run_until_complete(plotter.disconnect())
        loop.close()


@mcp.resource("plotter://dimensions")
def get_dimensions_resource(ctx: Context) -> str:
    """Plotter dimensions and capabilities."""
    import json
    
    return json.dumps({
        "width": config['plotter']['dimensions']['width'],
        "height": config['plotter']['dimensions']['height'],
        "margin": config['plotter']['dimensions']['margin'],
        "kinematics": "CoreXY",
        "pen_types": list(config['servo']['profiles'].keys())
    }, indent=2)


# Run server
if __name__ == "__main__":
    # Determine transport from config
    transport = config['mcp']['transport']
    
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        port = config['mcp'].get('http_port', 8001)
        mcp.run(transport="streamable-http", port=port)
    else:
        logger.error(f"Unknown transport: {transport}")
        sys.exit(1)
