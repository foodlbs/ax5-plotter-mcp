"""
RQ worker for processing plot jobs.
"""
import asyncio
import os
import sys
import logging
from redis import Redis
from rq import Worker, Queue, get_current_job
from rq.job import Job
import yaml

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.plotter.ax5 import AX5Plotter
from src.utils.svg_converter import SVGConverter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_plot_job(svg_file: str, options: dict = None) -> dict:
    """
    Process a plot job: convert SVG to G-code and execute on plotter.
    
    Args:
        svg_file: Path to SVG file
        options: Optional settings:
            - pen_type: Pen profile name
            - optimize: Whether to optimize paths
            
    Returns:
        dict: Job result with status and statistics
    """
    job = get_current_job()
    options = options or {}
    
    logger.info(f"Starting plot job {job.id} for {svg_file}")
    
    try:
        # Initialize metadata
        job.meta['stage'] = 'converting'
        job.meta['progress'] = 0
        job.save_meta()
        
        # Convert SVG to G-code
        converter = SVGConverter()
        gcode_file = converter.convert(
            svg_file,
            pen_profile=options.get('pen_type', 'ballpoint'),
            optimize=options.get('optimize', True)
        )
        
        # Estimate time
        estimated_time = converter.estimate_time(gcode_file)
        job.meta['estimated_time'] = estimated_time
        job.save_meta()
        
        logger.info(f"G-code generated: {gcode_file} (est. {estimated_time:.1f}s)")
        
        # Initialize plotter (sync wrapper for async code)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        plotter = AX5Plotter()
        
        # Connect
        job.meta['stage'] = 'connecting'
        job.save_meta()
        
        connected = loop.run_until_complete(plotter.connect())
        if not connected:
            raise Exception("Failed to connect to plotter")
        
        try:
            # Parse G-code for progress tracking
            with open(gcode_file, 'r') as f:
                commands = [
                    line.strip() for line in f
                    if line.strip() and not line.startswith(';')
                ]
            
            total_commands = len(commands)
            
            logger.info(f"Streaming {total_commands} commands to plotter")
            
            # Stream with progress updates
            job.meta['stage'] = 'plotting'
            job.meta['total_commands'] = total_commands
            job.save_meta()
            
            async def progress_callback(current, total):
                """Update job progress."""
                progress = (current / total) * 100
                job.meta['progress'] = progress
                job.meta['current_command'] = current
                job.save_meta()
                
                if current % 50 == 0:
                    logger.info(f"Progress: {current}/{total} ({progress:.1f}%)")
            
            # Execute plot
            success = loop.run_until_complete(
                plotter.stream_gcode(gcode_file, progress_callback)
            )
            
            if not success:
                raise Exception("G-code streaming failed")
            
            # Return home
            logger.info("Returning to home position")
            loop.run_until_complete(plotter.move_to(0, 0))
            
            result = {
                "status": "completed",
                "svg_file": svg_file,
                "gcode_file": gcode_file,
                "commands_executed": total_commands,
                "estimated_time": estimated_time
            }
            
            logger.info(f"Plot job {job.id} completed successfully")
            return result
            
        finally:
            # Always disconnect
            loop.run_until_complete(plotter.disconnect())
            loop.close()
            
    except Exception as e:
        logger.error(f"Plot job {job.id} failed: {e}")
        
        job.meta['error'] = str(e)
        job.save_meta()
        
        raise


def main():
    """Start RQ worker."""
    # Load configuration
    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    redis_config = config['redis']
    
    # Connect to Redis
    redis_conn = Redis(
        host=redis_config['host'],
        port=redis_config['port'],
        db=redis_config['db'],
        password=redis_config['password'],
        decode_responses=True
    )
    
    # Create queues (in priority order)
    high_queue = Queue('high', connection=redis_conn)
    normal_queue = Queue('normal', connection=redis_conn)
    low_queue = Queue('low', connection=redis_conn)
    
    logger.info("Starting RQ worker...")
    logger.info(f"Connected to Redis at {redis_config['host']}:{redis_config['port']}")
    logger.info("Listening on queues: high, normal, low")
    
    # Start worker
    worker = Worker(
        [high_queue, normal_queue, low_queue],
        connection=redis_conn,
        name='ax5-plotter-worker'
    )
    
    try:
        worker.work(with_scheduler=True)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise


if __name__ == '__main__':
    main()
