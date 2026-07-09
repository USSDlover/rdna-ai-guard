from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.schemas import TelemetryEvent


async def save_telemetry_event(
    event_data: TelemetryEvent,
    session: AsyncSession,
) -> TelemetryEvent:
    session.add(event_data)
    await session.commit()
    await session.refresh(event_data)
    return event_data


async def get_telemetry_event_by_id(
    event_id: str,
    session: AsyncSession,
) -> TelemetryEvent | None:
    return await session.get(TelemetryEvent, event_id)


async def update_telemetry_event(
    event_data: TelemetryEvent,
    session: AsyncSession,
) -> TelemetryEvent:
    session.add(event_data)
    await session.commit()
    await session.refresh(event_data)
    return event_data


async def get_recent_telemetry(
    session: AsyncSession,
    limit: int = 50,
) -> list[TelemetryEvent]:
    statement = (
        select(TelemetryEvent)
        .order_by(TelemetryEvent.timestamp.desc())
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())
