import { computed, inject, Injectable } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, scan } from 'rxjs/operators';

import { TelemetryStreamService } from '../../../core/services/telemetry-stream.service';
import { TelemetryEvent } from '../../../core/models/telemetry-event.model';

const MAX_FRAUD_BUFFER = 50;

@Injectable()
export class LedgerStateService {
  private readonly telemetryStream = inject(TelemetryStreamService);

  // Filter only FRAUD events from the stream
  private readonly fraudStream$ = this.telemetryStream
    .streamForLifecycle()
    .pipe(
      filter((event) => event.primary_vector === 'FRAUD'),
      scan((acc: TelemetryEvent[], event: TelemetryEvent) => 
        [event, ...acc].slice(0, MAX_FRAUD_BUFFER), []
      )
    );

  readonly fraudEvents = toSignal(this.fraudStream$, { initialValue: [] as TelemetryEvent[] });

  readonly totalFraudCount = computed(() => this.fraudEvents().length);

  readonly totalAmountAtRisk = computed(() =>
    this.fraudEvents().reduce((sum, e) => sum + e.transaction_amount, 0)
  );

  readonly averageRiskScore = computed(() => {
    const events = this.fraudEvents();
    if (!events.length) return 0;
    return Math.round(
      events.reduce((sum, e) => sum + e.risk_score, 0) / events.length
    );
  });
}