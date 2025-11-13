"""
Print Queue System for AX5 Plotter Photo Booth

Manages a queue of print jobs with user information and status tracking.
"""

import uuid
import time
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from dataclasses import dataclass, asdict
import threading
import queue

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Print job status."""
    QUEUED = "queued"
    PENDING_APPROVAL = "pending_approval"  # New status - waiting for manual approval
    PROCESSING = "processing"
    PLOTTING = "plotting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageStyle(Enum):
    """Available image processing styles."""
    CARTOON = "cartoon"
    SKETCH = "sketch"
    COMIC = "comic"
    OUTLINE = "outline"
    ARTISTIC = "artistic"
    MINIMAL = "minimal"


@dataclass
class PrintJob:
    """Represents a print job in the queue."""
    job_id: str
    name: str
    email: str
    image_path: str
    style: ImageStyle
    ai_provider: str
    status: JobStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    processed_image_path: Optional[str] = None
    gcode_path: Optional[str] = None
    retry_count: int = 0  # Track number of retries
    approved_for_print: bool = False  # Manual approval flag
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'job_id': self.job_id,
            'name': self.name,
            'email': self.email,
            'image_path': self.image_path,
            'style': self.style.value,
            'ai_provider': self.ai_provider,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message,
            'processed_image_path': self.processed_image_path,
            'gcode_path': self.gcode_path,
            'retry_count': self.retry_count,
            'approved_for_print': self.approved_for_print
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary."""
        return cls(
            job_id=data['job_id'],
            name=data['name'],
            email=data['email'],
            image_path=data['image_path'],
            style=ImageStyle(data['style']),
            ai_provider=data['ai_provider'],
            status=JobStatus(data['status']),
            created_at=data['created_at'],
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            error_message=data.get('error_message'),
            processed_image_path=data.get('processed_image_path'),
            gcode_path=data.get('gcode_path'),
            retry_count=data.get('retry_count', 0),
            approved_for_print=data.get('approved_for_print', False)
        )


class PrintQueue:
    """Manages print job queue."""
    
    def __init__(self):
        self.jobs: Dict[str, PrintJob] = {}
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.observers = []  # List of callbacks for status updates
        
    def add_job(
        self,
        name: str,
        email: str,
        image_path: str,
        style: ImageStyle,
        ai_provider: str = "None (Canny)",
        status: JobStatus = JobStatus.QUEUED,
        add_to_queue: bool = True
    ) -> str:
        """
        Add a new job to the queue.
        
        Args:
            name: User's name
            email: User's email
            image_path: Path to the processed image
            style: Image style (sketch, cartoon, etc.)
            ai_provider: AI provider used
            status: Initial job status (default: QUEUED)
            add_to_queue: Whether to add to processing queue immediately (default: True)
        
        Returns:
            str: Job ID
        """
        job_id = str(uuid.uuid4())
        
        job = PrintJob(
            job_id=job_id,
            name=name,
            email=email,
            image_path=image_path,
            style=style,
            ai_provider=ai_provider,
            status=status,
            created_at=time.time()
        )
        
        with self.lock:
            self.jobs[job_id] = job
            if add_to_queue:
                self.queue.put(job_id)
        
        logger.info(f"Added job {job_id} for {name} ({email})")
        self._notify_observers()
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[PrintJob]:
        """Get job by ID."""
        with self.lock:
            return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[PrintJob]:
        """Get all jobs sorted by creation time."""
        with self.lock:
            return sorted(
                self.jobs.values(),
                key=lambda j: j.created_at,
                reverse=True
            )
    
    def get_next_job(self) -> Optional[str]:
        """Get next job ID from queue (non-blocking)."""
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None
    
    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None
    ):
        """Update job status."""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = status
                
                if status == JobStatus.PROCESSING and job.started_at is None:
                    job.started_at = time.time()
                elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    job.completed_at = time.time()
                
                if error_message:
                    job.error_message = error_message
                
                logger.info(f"Job {job_id} status: {status.value}")
        
        self._notify_observers()
    
    def update_paths(
        self,
        job_id: str,
        processed_image_path: Optional[str] = None,
        gcode_path: Optional[str] = None
    ):
        """Update job file paths."""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if processed_image_path:
                    job.processed_image_path = processed_image_path
                if gcode_path:
                    job.gcode_path = gcode_path
        
        self._notify_observers()
    
    def cancel_job(self, job_id: str):
        """Cancel a queued job."""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job.status == JobStatus.QUEUED:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = time.time()
                    logger.info(f"Cancelled job {job_id}")
        
        self._notify_observers()
    
    def get_queue_position(self, job_id: str) -> Optional[int]:
        """Get position in queue (1-indexed)."""
        queued_jobs = [
            j for j in self.get_all_jobs()
            if j.status == JobStatus.QUEUED
        ]
        
        for i, job in enumerate(queued_jobs):
            if job.job_id == job_id:
                return i + 1
        
        return None
    
    def get_statistics(self) -> dict:
        """Get queue statistics."""
        jobs = self.get_all_jobs()
        
        return {
            'total': len(jobs),
            'queued': len([j for j in jobs if j.status == JobStatus.QUEUED]),
            'processing': len([j for j in jobs if j.status == JobStatus.PROCESSING]),
            'plotting': len([j for j in jobs if j.status == JobStatus.PLOTTING]),
            'completed': len([j for j in jobs if j.status == JobStatus.COMPLETED]),
            'failed': len([j for j in jobs if j.status == JobStatus.FAILED]),
            'cancelled': len([j for j in jobs if j.status == JobStatus.CANCELLED])
        }
    
    def add_observer(self, callback):
        """Add observer for queue changes."""
        self.observers.append(callback)
    
    def remove_observer(self, callback):
        """Remove observer."""
        if callback in self.observers:
            self.observers.remove(callback)
    
    def _notify_observers(self):
        """Notify all observers of queue changes."""
        for callback in self.observers:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error notifying observer: {e}")
    
    def save_to_file(self, filepath: str):
        """Save queue state to JSON file."""
        with self.lock:
            data = {
                'jobs': [job.to_dict() for job in self.jobs.values()]
            }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved queue to {filepath}")
    
    def load_from_file(self, filepath: str):
        """Load queue state from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            with self.lock:
                self.jobs.clear()
                for job_data in data['jobs']:
                    job = PrintJob.from_dict(job_data)
                    self.jobs[job.job_id] = job
                    
                    # Re-queue jobs that were queued
                    if job.status == JobStatus.QUEUED:
                        self.queue.put(job.job_id)
            
            logger.info(f"Loaded queue from {filepath}")
            self._notify_observers()
            
        except FileNotFoundError:
            logger.info(f"No queue file found at {filepath}")
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
