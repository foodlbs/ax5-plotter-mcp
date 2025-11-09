"""
FastAPI REST API for AX5 plotter control.
"""
import os
import sys
import uuid
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import yaml
from redis import Redis
from rq import Queue
from rq.job import Job
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
import asyncio
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.plotter.ax5 import AX5Plotter
from src.workers.plot_worker import process_plot_job
from src.api.auth import get_current_user, get_admin_user, check_rate_limit, User, get_db
from src.api.auth_routes import router as auth_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
with open('config/settings.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize FastAPI
app = FastAPI(
    title="AX5 Plotter Control API",
    description="REST API for controlling AX5 pen plotter",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config['api']['cors_origins'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)

# Redis and RQ setup
redis_conn = Redis(
    host=config['redis']['host'],
    port=config['redis']['port'],
    db=config['redis']['db'],
    password=config['redis']['password'],
    decode_responses=True
)

high_queue = Queue('high', connection=redis_conn)
normal_queue = Queue('normal', connection=redis_conn)
low_queue = Queue('low', connection=redis_conn)


# Request/Response Models
class PlotRequest(BaseModel):
    """Plot job submission request."""
    svg_file: str = Field(..., description="Path to SVG file")
    priority: str = Field("normal", description="Job priority: high, normal, low")
    pen_type: str = Field("ballpoint", description="Pen type profile")
    optimize: bool = Field(True, description="Apply path optimization")


class PlotResponse(BaseModel):
    """Plot job submission response."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Initial job status")
    queue_position: int = Field(..., description="Position in queue")


class JobStatus(BaseModel):
    """Job status response."""
    id: str
    status: str
    progress: float = 0
    stage: Optional[str] = None
    current_command: Optional[int] = None
    total_commands: Optional[int] = None
    estimated_time: Optional[float] = None
    enqueued_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict] = None


class PlotterStatus(BaseModel):
    """Current plotter status."""
    state: str
    position: dict
    machine_position: dict
    homed: bool
    connected: bool


# API Endpoints

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "AX5 Plotter Control API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/api/plots", response_model=PlotResponse)
async def submit_plot(
    request: PlotRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit SVG file for plotting.
    
    Requires authentication. Returns job ID and initial status.
    Rate limited based on user account settings.
    """
    # Check rate limit
    check_rate_limit(current_user, "submit_plot", db)
    
    # Validate file exists
    if not os.path.exists(request.svg_file):
        raise HTTPException(404, f"File not found: {request.svg_file}")
    
    # Validate file extension
    if not request.svg_file.lower().endswith('.svg'):
        raise HTTPException(400, "File must be SVG format")
    
    # Select queue by priority
    if request.priority == "high":
        queue = high_queue
    elif request.priority == "low":
        queue = low_queue
    else:
        queue = normal_queue
    
    # Enqueue job with user info
    job = queue.enqueue(
        process_plot_job,
        request.svg_file,
        options={
            'pen_type': request.pen_type,
            'optimize': request.optimize
        },
        timeout=config['queue']['default_timeout'],
        result_ttl=config['queue']['result_ttl'],
        meta={'user_id': current_user.id, 'username': current_user.username}
    )
    
    # Update user stats
    current_user.total_jobs += 1
    db.commit()
    
    logger.info(f"Job {job.id} enqueued by user {current_user.username} for {request.svg_file}")
    
    return PlotResponse(
        job_id=job.id,
        status="queued",
        queue_position=queue.count
    )


@app.post("/api/plots/upload")
async def upload_svg(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload SVG file for plotting.
    
    Returns file path for use in submit_plot.
    Requires authentication.
    """
    # Validate file type
    if not file.filename.endswith('.svg'):
        raise HTTPException(400, "File must be SVG format")
    
    # Check file size
    content = await file.read()
    if len(content) > config['api']['max_upload_size']:
        raise HTTPException(413, "File too large")
    
    # Save file with user prefix
    upload_dir = config['api']['upload_dir']
    os.makedirs(upload_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(upload_dir, f"{current_user.username}_{file_id}.svg")
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    logger.info(f"File uploaded by {current_user.username}: {file.filename} -> {file_path}")
    
    return {
        "file_path": file_path,
        "file_id": file_id,
        "filename": file.filename,
        "size": len(content)
    }


@app.get("/api/plots/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of specific job."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        return JobStatus(
            id=job_id,
            status=job.get_status(),
            progress=job.meta.get('progress', 0),
            stage=job.meta.get('stage'),
            current_command=job.meta.get('current_command'),
            total_commands=job.meta.get('total_commands'),
            estimated_time=job.meta.get('estimated_time'),
            enqueued_at=job.enqueued_at.isoformat() if job.enqueued_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            finished_at=job.ended_at.isoformat() if job.ended_at else None,
            error=job.meta.get('error') if job.is_failed else None,
            result=job.result if job.is_finished else None
        )
        
    except Exception as e:
        raise HTTPException(404, f"Job not found: {str(e)}")


@app.get("/api/plots/{job_id}/stream")
async def stream_job_progress(job_id: str):
    """
    Stream job progress via Server-Sent Events.
    
    Client should connect and listen for progress updates.
    """
    async def event_generator():
        last_progress = -1
        last_status = None
        
        while True:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                
                status = job.get_status()
                progress = job.meta.get('progress', 0)
                
                # Send update if changed
                if progress != last_progress or status != last_status:
                    yield {
                        "event": "progress",
                        "data": json.dumps({
                            "progress": progress,
                            "status": status,
                            "stage": job.meta.get('stage'),
                            "current_command": job.meta.get('current_command'),
                            "total_commands": job.meta.get('total_commands')
                        })
                    }
                    
                    last_progress = progress
                    last_status = status
                
                # End stream on completion
                if job.is_finished or job.is_failed:
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "status": status,
                            "result": job.result,
                            "error": job.meta.get('error')
                        })
                    }
                    break
                
                await asyncio.sleep(config['queue']['job_monitoring_interval'])
                
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }
                break
    
    return EventSourceResponse(event_generator())


@app.delete("/api/plots/{job_id}")
async def cancel_job(job_id: str):
    """Cancel running or queued job."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        if job.is_started or job.is_queued:
            job.cancel()
            logger.info(f"Job {job_id} cancelled")
            return {"status": "cancelled", "job_id": job_id}
        else:
            return {
                "status": "cannot_cancel",
                "reason": f"Job is {job.get_status()}"
            }
            
    except Exception as e:
        raise HTTPException(404, f"Job not found: {str(e)}")


@app.get("/api/plots")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50
):
    """
    List jobs with optional status filter.
    
    Status options: queued, started, finished, failed
    """
    from rq.registry import (
        StartedJobRegistry,
        FinishedJobRegistry,
        FailedJobRegistry,
        ScheduledJobRegistry
    )
    
    jobs = []
    
    registries = {
        'started': StartedJobRegistry(queue=normal_queue),
        'finished': FinishedJobRegistry(queue=normal_queue),
        'failed': FailedJobRegistry(queue=normal_queue),
    }
    
    # Get jobs from registries
    for reg_name, registry in registries.items():
        if status is None or status == reg_name:
            for job_id in registry.get_job_ids()[:limit]:
                try:
                    job = Job.fetch(job_id, connection=redis_conn)
                    jobs.append({
                        "id": job.id,
                        "status": job.get_status(),
                        "progress": job.meta.get('progress', 0),
                        "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None
                    })
                except:
                    pass
    
    return jobs


@app.get("/api/plotter/status", response_model=PlotterStatus)
async def get_plotter_status():
    """Get current plotter status and position."""
    plotter = AX5Plotter()
    
    try:
        await plotter.connect()
        status = await plotter.get_status()
        connected = await plotter.is_connected()
        
        return PlotterStatus(
            state=status['state'],
            position=status['position'],
            machine_position=status['machine_position'],
            homed=status.get('homed', False),
            connected=connected
        )
        
    except Exception as e:
        return PlotterStatus(
            state="error",
            position={"x": 0, "y": 0, "z": 0},
            machine_position={"x": 0, "y": 0, "z": 0},
            homed=False,
            connected=False
        )
    finally:
        if plotter:
            await plotter.disconnect()


@app.post("/api/plotter/home")
async def home_plotter():
    """Execute homing cycle."""
    plotter = AX5Plotter()
    
    try:
        await plotter.connect()
        success = await plotter.home()
        
        if success:
            return {"status": "success", "message": "Homing complete"}
        else:
            raise HTTPException(500, "Homing failed")
            
    except Exception as e:
        raise HTTPException(500, f"Homing error: {str(e)}")
    finally:
        await plotter.disconnect()


@app.post("/api/plotter/pen")
async def control_pen(down: bool):
    """Manual pen control."""
    plotter = AX5Plotter()
    
    try:
        await plotter.connect()
        await plotter.pen_control(down)
        
        return {
            "status": "success",
            "pen": "down" if down else "up"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Pen control error: {str(e)}")
    finally:
        await plotter.disconnect()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        redis_conn.ping()
        redis_ok = True
    except:
        redis_ok = False
    
    return {
        "status": "healthy" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
        "queues": {
            "high": high_queue.count,
            "normal": normal_queue.count,
            "low": low_queue.count
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config['api']['host'],
        port=config['api']['port'],
        reload=True
    )
