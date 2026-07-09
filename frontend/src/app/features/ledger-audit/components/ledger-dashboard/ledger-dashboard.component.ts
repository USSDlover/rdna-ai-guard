import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';

import { TelemetryEvent } from '../../../../core/models/telemetry-event.model';
import { TelemetryDetailModalComponent } from '../../../cyber-grid/components/telemetry-detail-modal/telemetry-detail-modal.component';
import { LedgerStateService } from '../../data-access/ledger-state.service';
import { LedgerChartComponent } from '../ledger-chart/ledger-chart.component';

@Component({
  selector: 'app-ledger-dashboard',
  imports: [CurrencyPipe, DatePipe, LedgerChartComponent, TelemetryDetailModalComponent],
  templateUrl: './ledger-dashboard.component.html',
  styleUrl: './ledger-dashboard.component.css',
})
export class LedgerDashboardComponent {
  protected readonly state = inject(LedgerStateService);

  protected readonly selectedEventId = signal<string | null>(null);

  protected readonly selectedEvent = computed(() => {
    const eventId = this.selectedEventId();
    if (!eventId) {
      return null;
    }

    return this.state.events().find((event) => event.id === eventId) ?? null;
  });

  protected readonly statusBadgeById = computed(() => {
    const badges = new Map<string, string>();

    for (const event of this.state.fraudEvents()) {
      badges.set(
        event.id,
        event.status === 'ESCALATED'
          ? 'bg-red-700 text-white ring-1 ring-red-500/70'
          : 'bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/40',
      );
    }

    return badges;
  });

  protected readonly riskToneById = computed(() => {
    const tones = new Map<string, string>();

    for (const event of this.state.fraudEvents()) {
      if (event.risk_score > 80) {
        tones.set(event.id, 'text-red-400 font-semibold');
      } else if (event.risk_score >= 50) {
        tones.set(event.id, 'text-amber-300 font-medium');
      } else {
        tones.set(event.id, 'text-slate-300');
      }
    }

    return tones;
  });

  protected statusBadgeClasses(event: TelemetryEvent): string {
    return (
      this.statusBadgeById().get(event.id) ??
      'bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/40'
    );
  }

  protected riskScoreClasses(event: TelemetryEvent): string {
    return this.riskToneById().get(event.id) ?? 'text-slate-300';
  }

  protected selectEvent(event: TelemetryEvent): void {
    this.selectedEventId.set(event.id);
  }

  protected closeDetail(): void {
    this.selectedEventId.set(null);
  }
}
