import { computed, inject, Injectable, signal } from '@angular/core';

import { TelemetryStreamService } from '../../../core/services/telemetry-stream.service';
import { TelemetryEvent } from '../../../core/models/telemetry-event.model';

const MAX_EVENT_BUFFER = 50;

@Injectable()
export class CyberStateService {
  private readonly telemetryStream = inject(TelemetryStreamService);

  readonly events = signal<TelemetryEvent[]>([]);

  readonly totalThreatsCount = computed(
    () =>
      this.events().filter(
        (event) => event.primary_vector !== 'NONE' || event.risk_score >= 50,
      ).length,
  );

  readonly escalatedCount = computed(
    () => this.events().filter((event) => event.status === 'ESCALATED').length,
  );

  readonly averageRiskScore = computed(() => {
    const snapshot = this.events();
    if (!snapshot.length) {
      return 0;
    }

    const total = snapshot.reduce((sum, event) => sum + event.risk_score, 0);
    return Math.round(total / snapshot.length);
  });

  constructor() {
    this.telemetryStream.streamForLifecycle().subscribe((event) => {
      this.ingestEvent(event);
    });
  }

  private ingestEvent(event: TelemetryEvent): void {
    this.events.update((current) => [event, ...current].slice(0, MAX_EVENT_BUFFER));
  }
}
