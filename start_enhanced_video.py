#!/usr/bin/env python3
"""
Enhanced Video Generation System Startup Script

This script demonstrates how to properly initialize and start the enhanced
video generation system with all the new modern features.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from modules.video.video_generation import start_queue_processor, stop_queue_processor
from modules.video.video_analytics import analytics_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_generation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class EnhancedVideoSystemManager:
    """Manager for the enhanced video generation system."""
    
    def __init__(self):
        self.running = False
        self.startup_time = None
        
    async def start_system(self):
        """Start all components of the enhanced video generation system."""
        try:
            logger.info("🚀 Starting Enhanced Video Generation System...")
            self.startup_time = datetime.now()
            
            # Start the video generation queue processor
            logger.info("📊 Starting video generation queue processor...")
            start_queue_processor()
            
            # Initialize analytics system
            logger.info("📈 Initializing analytics system...")
            analytics_collection = analytics_manager.get_analytics_collection()
            if analytics_collection:
                logger.info("✅ Analytics system initialized successfully")
            else:
                logger.warning("⚠️ Analytics system initialization failed")
            
            # System is now running
            self.running = True
            
            logger.info("✅ Enhanced Video Generation System started successfully!")
            logger.info(f"🕐 Startup time: {self.startup_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Log system capabilities
            await self._log_system_capabilities()
            
        except Exception as e:
            logger.error(f"❌ Failed to start Enhanced Video Generation System: {e}")
            raise
    
    async def stop_system(self):
        """Stop all components of the enhanced video generation system."""
        try:
            logger.info("🛑 Stopping Enhanced Video Generation System...")
            
            # Stop the queue processor
            logger.info("📊 Stopping video generation queue processor...")
            stop_queue_processor()
            
            # Mark system as stopped
            self.running = False
            
            if self.startup_time:
                uptime = datetime.now() - self.startup_time
                logger.info(f"⏰ System uptime: {uptime}")
            
            logger.info("✅ Enhanced Video Generation System stopped successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error stopping Enhanced Video Generation System: {e}")
    
    async def _log_system_capabilities(self):
        """Log the capabilities of the enhanced system."""
        capabilities = [
            "🎬 Multiple Quality Tiers (Standard/HD/Premium)",
            "📐 Custom Aspect Ratios (9:16, 16:9, 1:1, 21:9)",
            "🎨 AI Prompt Enhancement",
            "📊 Advanced Analytics & Insights",
            "🎛️ Smart Queue Management",
            "🔄 Real-time Progress Tracking",
            "💳 Enhanced Token Management",
            "📱 Modern Interactive UI",
            "🚀 High Performance & Scalability"
        ]
        
        logger.info("🌟 System Capabilities:")
        for capability in capabilities:
            logger.info(f"  {capability}")
    
    async def health_check(self):
        """Perform a health check of the system components."""
        health_status = {
            "system_running": self.running,
            "queue_processor": False,
            "analytics_system": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Check queue processor
        from modules.video.video_generation import queue_processor_task
        if queue_processor_task and not queue_processor_task.done():
            health_status["queue_processor"] = True
        
        # Check analytics system
        analytics_collection = analytics_manager.get_analytics_collection()
        if analytics_collection:
            health_status["analytics_system"] = True
        
        return health_status

async def main():
    """Main function to run the enhanced video generation system."""
    system_manager = EnhancedVideoSystemManager()
    
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(system_manager.stop_system())
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the enhanced video generation system
        await system_manager.start_system()
        
        # Keep the system running
        logger.info("🎯 System is now ready to handle video generation requests!")
        logger.info("💡 Use /video <prompt> in Telegram to test the enhanced features")
        
        # Periodic health checks
        while system_manager.running:
            await asyncio.sleep(60)  # Wait 1 minute
            
            # Perform health check
            health = await system_manager.health_check()
            logger.debug(f"Health check: {health}")
            
            # Log system status
            if health["system_running"] and health["queue_processor"]:
                logger.info("💚 System healthy - all components running")
            else:
                logger.warning(f"⚠️ System health issues detected: {health}")
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        await system_manager.stop_system()

def run_demo():
    """Run a quick demo of the enhanced features."""
    print("🎬 Enhanced Video Generation System Demo")
    print("=" * 50)
    print()
    print("🌟 New Features:")
    print("  • Multiple Quality Tiers (Standard/HD/Premium)")
    print("  • AI Prompt Enhancement")
    print("  • Real-time Progress Tracking")
    print("  • Smart Queue Management")
    print("  • Advanced Analytics")
    print("  • Custom Aspect Ratios")
    print("  • Interactive UI Components")
    print()
    print("📱 Usage:")
    print("  /video <your prompt>     - Create video with quality selection")
    print("  /token                   - View enhanced token dashboard")
    print("  /addt <user> <tokens>   - Admin: Add tokens with notifications")
    print()
    print("🎯 Quality Tiers:")
    print("  Standard (10 tokens)  - Fast, good quality")
    print("  HD (15 tokens)        - Enhanced quality + AI optimization")
    print("  Premium (25 tokens)   - Highest quality + priority queue")
    print()
    print("📐 Aspect Ratios:")
    print("  9:16 (Vertical)       - Perfect for mobile/stories")
    print("  16:9 (Landscape)      - Standard widescreen")
    print("  1:1 (Square)          - Social media posts")
    print("  21:9 (Cinematic)      - Ultra-wide cinematic")
    print()
    print("🚀 Ready to start the enhanced system!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_demo()
    else:
        print("🎬 Enhanced Video Generation System")
        print("Starting system components...")
        
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            sys.exit(1)