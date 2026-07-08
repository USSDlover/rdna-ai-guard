import asyncio
import logging

from app.models.schemas import TelemetryEvent

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_MAXSIZE = 100


class SSEBroadcastManager:
    def __init__(self, queue_maxsize: int = DEFAULT_QUEUE_MAXSIZE) -> None:
        self._subscribers: set[asyncio.Queue[TelemetryEvent]] = set()
        self._queue_maxsize = queue_maxsize

    async def subscribe(self) -> asyncio.Queue[TelemetryEvent]:
        queue: asyncio.Queue[TelemetryEvent] = asyncio.Queue(maxsize=self._queue_maxsize)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[TelemetryEvent]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: TelemetryEvent) -> None:
        stale_queues: list[asyncio.Queue[TelemetryEvent]] = []

        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Dropping unresponsive SSE subscriber queue for event %s",
                    event.id,
                )
                stale_queues.append(queue)

        for queue in stale_queues:
            self.unsubscribe(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


broadcast_manager = SSEBroadcastManager()
