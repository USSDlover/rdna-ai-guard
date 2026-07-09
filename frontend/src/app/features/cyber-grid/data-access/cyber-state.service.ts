import { computed, inject, Injectable } from '@angular/core';

import { TelemetryStateService } from '../../../core/services/telemetry-state.service';

@Injectable({ providedIn: 'root' })
export class CyberStateService {
  private readonly telemetryState = inject(TelemetryStateService);

  readonly events = this.telemetryState.events;

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
}
