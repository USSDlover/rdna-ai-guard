import { computed, inject, Injectable, signal } from '@angular/core';

import { TelemetryStreamService } from '../../../core/services/telemetry-stream.service';
import { TelemetryEvent } from '../../../core/models/telemetry-event.model';

const MAX_EVENT_BUFFER = 50;

@Injectable()
export class LedgerStateService {
  private readonly telemetryStream = inject(TelemetryStreamService);

  private readonly eventBuffer: TelemetryEvent[] = [];

  readonly events = signal<readonly TelemetryEvent[]>([]);

  readonly fraudEvents = computed(() =>
    this.events().filter(
      (event) => event.primary_vector === 'FRAUD' || event.transaction_amount > 5000,
    ),
  );

  readonly totalFraudVolume = computed(() =>
    this.fraudEvents().reduce((sum, event) => sum + event.transaction_amount, 0),
  );

  readonly highVelocityAlertsCount = computed(
    () => this.fraudEvents().filter((event) => event.risk_score > 80).length,
  );

  readonly averageFraudAmount = computed(() => {
    const snapshot = this.fraudEvents();
    if (!snapshot.length) {
      return 0;
    }

    const total = snapshot.reduce((sum, event) => sum + event.transaction_amount, 0);
    return Math.round((total / snapshot.length) * 100) / 100;
  });

  constructor() {
    this.telemetryStream.streamForLifecycle().subscribe((event) => {
      this.ingestEvent(event);
    });
  }

  private ingestEvent(event: TelemetryEvent): void {
    this.eventBuffer.unshift(event);

    if (this.eventBuffer.length > MAX_EVENT_BUFFER) {
      this.eventBuffer.length = MAX_EVENT_BUFFER;
    }

    this.events.set(Object.freeze([...this.eventBuffer]));
  }
}
