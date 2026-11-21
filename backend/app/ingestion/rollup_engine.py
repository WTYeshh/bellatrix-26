import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from backend.app.models import MetricRecord, MetricRollup

async def process_rollups_and_retention(db: AsyncSession, metric: MetricRecord):
    """
    Downsamples real metric samples into 1m, 5m, and 1h rollups,
    and applies automated retention pruning.
    """
    ts = metric.timestamp_utc
    if ts.tzinfo is not None:
        ts = ts.replace(tzinfo=None)

    # 1. 1-Minute Bucket
    b_1m = ts.replace(second=0, microsecond=0)
    # 2. 5-Minute Bucket
    b_5m = ts.replace(minute=ts.minute - (ts.minute % 5), second=0, microsecond=0)
    # 3. 1-Hour Bucket
    b_1h = ts.replace(minute=0, second=0, microsecond=0)

    buckets = [("1m", b_1m), ("5m", b_5m), ("1h", b_1h)]

    for interval_name, b_start in buckets:
        stmt = select(MetricRollup).where(
            MetricRollup.source_id == metric.source_id,
            MetricRollup.interval == interval_name,
            MetricRollup.bucket_start_utc == b_start
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            prev_cnt = existing.sample_count
            new_cnt = prev_cnt + 1
            existing.cpu_avg = round(((existing.cpu_avg * prev_cnt) + metric.cpu_usage) / new_cnt, 2)
            existing.cpu_min = min(existing.cpu_min, metric.cpu_usage)
            existing.cpu_max = max(existing.cpu_max, metric.cpu_usage)
            existing.memory_avg = round(((existing.memory_avg * prev_cnt) + metric.memory_usage) / new_cnt, 2)
            existing.disk_avg = round(((existing.disk_avg * prev_cnt) + metric.disk_usage) / new_cnt, 2)
            existing.latency_avg = round(((existing.latency_avg * prev_cnt) + metric.latency_ms) / new_cnt, 2)
            existing.sample_count = new_cnt
        else:
            rollup = MetricRollup(
                source_id=metric.source_id,
                interval=interval_name,
                bucket_start_utc=b_start,
                cpu_avg=metric.cpu_usage,
                cpu_min=metric.cpu_usage,
                cpu_max=metric.cpu_usage,
                memory_avg=metric.memory_usage,
                disk_avg=metric.disk_usage,
                latency_avg=metric.latency_ms,
                sample_count=1
            )
            db.add(rollup)
    await db.flush()

async def prune_retention(db: AsyncSession):
    """Enforces retention policy: prunes raw samples > 48h and rollups > 30d."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    raw_cutoff = now_utc - datetime.timedelta(hours=48)
    rollup_cutoff = now_utc - datetime.timedelta(days=30)

    await db.execute(delete(MetricRecord).where(MetricRecord.timestamp_utc < raw_cutoff))
    await db.execute(delete(MetricRollup).where(MetricRollup.bucket_start_utc < rollup_cutoff))
