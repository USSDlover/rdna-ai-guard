import { computed, inject, Injectable } from '@angular/core';

import { TelemetryStateService } from '../../../core/services/telemetry-state.service';

@Injectable({ providedIn: 'root' })
export class LedgerStateService {
  private readonly telemetryState = inject(TelemetryStateService);

  readonly events = this.telemetryState.events;

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
}
