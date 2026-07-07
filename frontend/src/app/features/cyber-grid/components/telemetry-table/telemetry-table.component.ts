import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';

import { TelemetryEvent } from '../../../../core/models/telemetry-event.model';

@Component({
  selector: 'app-telemetry-table',
  imports: [CurrencyPipe, DatePipe],
  templateUrl: './telemetry-table.component.html',
  styleUrl: './telemetry-table.component.css',
})
export class TelemetryTableComponent {
  readonly events = input.required<TelemetryEvent[]>();

  protected rowClasses(event: TelemetryEvent): string {
    if (event.status === 'ESCALATED') {
      return 'border-l-4 border-red-500 bg-red-950/30 animate-pulse';
    }

    return 'border-l-4 border-emerald-500/70 bg-emerald-950/10';
  }

  protected statusBadgeClasses(event: TelemetryEvent): string {
    if (event.status === 'ESCALATED') {
      return 'bg-red-500/20 text-red-300 ring-1 ring-red-500/60';
    }

    return 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/40';
  }

  protected vectorBadgeClasses(event: TelemetryEvent): string {
    switch (event.primary_vector) {
      case 'CYBER':
        return 'bg-cyan-500/15 text-cyan-300';
      case 'FRAUD':
        return 'bg-amber-500/15 text-amber-300';
      default:
        return 'bg-slate-700/60 text-slate-300';
    }
  }

  protected riskScoreClasses(score: number): string {
    if (score >= 75) {
      return 'text-red-400 font-semibold';
    }

    if (score >= 40) {
      return 'text-amber-300 font-medium';
    }

    return 'text-emerald-300';
  }
}
