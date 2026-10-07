"""Background worker process executing scheduled jobs and queue consumers."""

import asyncio
import signal
import sys

from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.model_factory import resolve_model
from app.memory.manager import RivalMemory
from app.scheduler.scheduler import SchedulerEngine

logger = get_logger("rivalscope.worker")


async def main():
    settings = get_settings()
    setup_logging(level="DEBUG" if settings.debug else "INFO")
    logger.info(f"Starting RivalScope background worker ({settings.env} mode)")

    model = resolve_model("worker-default-model")
    memory = RivalMemory()
    scheduler = SchedulerEngine(model=model, memory=memory)

    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received; stopping scheduler...")
        scheduler.stop()
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # Signal handling on Windows
            pass

    # Start scheduler loop in background
    poll_task = asyncio.create_task(
        scheduler.run_poll_loop(poll_interval_seconds=settings.scheduler_poll_interval_seconds)
    )

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        handle_signal()
    finally:
        poll_task.cancel()
        logger.info("Worker process terminated gracefully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
