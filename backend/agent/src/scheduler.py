"""
APScheduler-based job scheduler for automated assignment processing.
Implements daily scheduled job execution with error handling and logging.
"""

import logging
import asyncio
from typing import Optional
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from .config import settings
from .agent import AutomationAgent

logger = logging.getLogger(__name__)

class AssignmentScheduler:
    """Scheduler for automated assignment processing jobs"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.agent: Optional[AutomationAgent] = None
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Setup event listeners for job execution monitoring"""
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
    
    def _job_executed(self, event):
        """Handle successful job execution"""
        logger.info(f"Job {event.job_id} executed successfully at {datetime.now()}")
    
    def _job_error(self, event):
        """Handle job execution errors"""
        logger.error(f"Job {event.job_id} failed: {event.exception}")
        logger.error(f"Traceback: {event.traceback}")
    
    async def initialize(self):
        """Initialize the scheduler and automation agent"""
        logger.info("Initializing assignment scheduler...")
        
        try:
            # Initialize the automation agent
            self.agent = AutomationAgent()
            await self.agent.initialize()
            
            # Add the daily sync job
            self._add_daily_sync_job()
            
            logger.info("Assignment scheduler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _add_daily_sync_job(self):
        """Add the daily assignment sync job to the scheduler"""
        try:
            # Parse the cron expression from settings
            cron_parts = settings.SYNC_SCHEDULE_CRON.split()
            
            if len(cron_parts) != 5:
                raise ValueError(f"Invalid cron expression: {settings.SYNC_SCHEDULE_CRON}")
            
            minute, hour, day, month, day_of_week = cron_parts
            
            # Create cron trigger
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
            # Add the job
            self.scheduler.add_job(
                func=self._run_daily_sync,
                trigger=trigger,
                id='daily_assignment_sync',
                name='Daily Assignment Sync',
                replace_existing=True,
                max_instances=1  # Prevent overlapping executions
            )
            
            logger.info(f"Daily sync job scheduled with cron: {settings.SYNC_SCHEDULE_CRON}")
            
        except Exception as e:
            logger.error(f"Failed to add daily sync job: {e}")
            raise
    
    async def _run_daily_sync(self):
        """Execute the daily assignment sync process"""
        logger.info("Starting scheduled daily assignment sync...")
        
        try:
            if not self.agent:
                raise RuntimeError("Automation agent not initialized")
            
            # Run the daily sync process
            await self.agent.run_daily_sync()
            
            logger.info("Scheduled daily assignment sync completed successfully")
            
        except Exception as e:
            logger.error(f"Scheduled daily assignment sync failed: {e}")
            # Don't re-raise to prevent scheduler from stopping
    
    def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("Assignment scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def stop(self):
        """Stop the scheduler"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("Assignment scheduler stopped")
            else:
                logger.warning("Scheduler not running or not initialized")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def cleanup(self):
        """Cleanup scheduler and agent resources"""
        logger.info("Cleaning up scheduler resources...")
        
        try:
            if self.agent:
                await self.agent.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up agent: {e}")
        
        logger.info("Scheduler cleanup completed")
    
    def get_job_status(self) -> dict:
        """Get status information about scheduled jobs"""
        jobs = []
        
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return {
            'scheduler_running': self.scheduler.running,
            'jobs': jobs
        }
    
    async def run_sync_now(self):
        """Manually trigger a sync job (for testing/debugging)"""
        logger.info("Manually triggering assignment sync...")
        
        try:
            if not self.agent:
                raise RuntimeError("Automation agent not initialized")
            
            await self.agent.run_daily_sync()
            logger.info("Manual assignment sync completed successfully")
            
        except Exception as e:
            logger.error(f"Manual assignment sync failed: {e}")
            raise