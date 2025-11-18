#!/usr/bin/env python3
"""
Automated Assignment Solver Agent

This script runs the automation agent that:
1. Fetches assignments from Google Classroom
2. Generates solutions using Google Gemini API
3. Uploads results to the backend API

The agent can run in two modes:
- Scheduled mode: Runs continuously with daily scheduled jobs
- One-time mode: Runs a single sync and exits
"""

import asyncio
import logging
import signal
import sys
from argparse import ArgumentParser

from src.config import settings
from src.scheduler import AssignmentScheduler
from src.agent import AutomationAgent
from src.logging_config import setup_logging

# Configure enhanced logging
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_file=settings.LOG_FILE,
    enable_console=True,
    enable_file=True,
    enable_rotation=True
)

logger = logging.getLogger(__name__)

class AgentRunner:
    """Main runner for the automation agent"""
    
    def __init__(self):
        self.scheduler: AssignmentScheduler = None
        self.running = False
    
    async def run_scheduled(self):
        """Run the agent in scheduled mode with daily jobs"""
        logger.info("Starting Automated Assignment Solver Agent in scheduled mode")
        
        try:
            # Initialize and start the scheduler
            self.scheduler = AssignmentScheduler()
            await self.scheduler.initialize()
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start the scheduler
            self.scheduler.start()
            self.running = True
            
            logger.info("Agent is running with scheduled jobs. Press Ctrl+C to stop.")
            
            # Keep the main thread alive
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise
        finally:
            await self._shutdown()
    
    async def run_once(self):
        """Run a single sync operation and exit"""
        logger.info("Starting Automated Assignment Solver Agent in one-time mode")
        
        agent = None
        try:
            agent = AutomationAgent()
            await agent.initialize()
            
            # Run daily sync once
            await agent.run_daily_sync()
            
            logger.info("One-time sync completed successfully")
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise
        finally:
            if agent:
                await agent.cleanup()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _shutdown(self):
        """Gracefully shutdown the agent"""
        logger.info("Shutting down agent...")
        
        try:
            if self.scheduler:
                try:
                    await self.scheduler.cleanup()
                except Exception as e:
                    logger.error(f"Error during scheduler cleanup: {e}")
                
                try:
                    self.scheduler.stop()
                except Exception as e:
                    logger.error(f"Error stopping scheduler: {e}")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            logger.info("Agent shutdown completed")

async def main():
    """Main entry point for the automation agent"""
    parser = ArgumentParser(description="Automated Assignment Solver Agent")
    parser.add_argument(
        '--mode',
        choices=['scheduled', 'once'],
        default='scheduled',
        help='Run mode: scheduled (continuous with daily jobs) or once (single sync)'
    )
    parser.add_argument(
        '--sync-now',
        action='store_true',
        help='Trigger an immediate sync (only in scheduled mode)'
    )
    parser.add_argument(
        '--assignment-id',
        type=str,
        help='Process a specific assignment by ID'
    )
    parser.add_argument(
        '--user-id',
        type=str,
        help='User ID for assignment processing'
    )
    
    args = parser.parse_args()
    
    runner = AgentRunner()
    
    try:
        # Check if processing a single assignment
        if args.assignment_id:
            logger.info(f"Processing single assignment: {args.assignment_id}")
            agent = AutomationAgent(user_id=args.user_id)
            await agent.initialize()
            try:
                await agent.process_single_assignment(args.assignment_id)
            finally:
                await agent.cleanup()
        elif args.mode == 'scheduled':
            if args.sync_now:
                # Initialize scheduler and run sync immediately
                scheduler = AssignmentScheduler()
                await scheduler.initialize()
                await scheduler.run_sync_now()
            else:
                # Run in scheduled mode
                await runner.run_scheduled()
        else:
            # Run once and exit
            await runner.run_once()
            
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())