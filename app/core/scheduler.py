"""APScheduler-based cron for daily briefing generation."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

scheduler = AsyncIOScheduler()


async def scheduled_briefing_job():
    """Generate briefing for the demo user at the configured hour.

    This import is deferred to avoid circular dependencies.
    """
    from app.services.pipeline import generate_briefing

    try:
        result = await generate_briefing(user_id="demo-user")
        print(f"[Scheduler] Briefing generated: {result.briefing_id}")
    except Exception as e:
        print(f"[Scheduler] Failed to generate briefing: {e}")


def start_scheduler():
    """Start the cron scheduler. Called during app lifespan."""
    scheduler.add_job(
        scheduled_briefing_job,
        "cron",
        hour=settings.briefing_schedule_hour,
        minute=0,
        id="daily_briefing",
        replace_existing=True,
    )
    scheduler.start()
    print(
        f"[Scheduler] Daily briefing scheduled at {settings.briefing_schedule_hour}:00"
    )


def stop_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
