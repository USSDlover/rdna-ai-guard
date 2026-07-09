import { DatePipe } from '@angular/common';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { Component, computed, input, signal } from '@angular/core';

import { TelemetryEvent } from '../../../../core/models/telemetry-event.model';
import { TelemetryDetailModalComponent } from '../telemetry-detail-modal/telemetry-detail-modal.component';

const ROW_HEIGHT_PX = 52;

@Component({
  selector: 'app-telemetry-table',
  imports: [DatePipe, ScrollingModule, TelemetryDetailModalComponent],
  templateUrl: './telemetry-table.component.html',
  styleUrl: './telemetry-table.component.css',
})
export class TelemetryTableComponent {
  readonly events = input.required<readonly TelemetryEvent[]>();

  protected readonly selectedEventId = signal<string | null>(null);

  protected readonly selectedEvent = computed(() => {
    const eventId = this.selectedEventId();
    if (!eventId) {
      return null;
    }

    return this.events().find((event) => event.id === eventId) ?? null;
  });

  protected readonly rowHeight = ROW_HEIGHT_PX;

  protected readonly hasEvents = computed(() => this.events().length > 0);

  protected readonly rowToneById = computed(() => {
    const tones = new Map<string, string>();

    for (const event of this.events()) {
      tones.set(
        event.id,
        event.status === 'ESCALATED'
          ? 'bg-red-950/35 hover:bg-red-950/50 border-l-4 border-red-600/80'
          : 'bg-slate-900/70 hover:bg-slate-800/80 border-l-4 border-transparent',
      );
    }

    return tones;
  });

  protected readonly statusBadgeById = computed(() => {
    const badges = new Map<string, string>();

    for (const event of this.events()) {
      badges.set(
        event.id,
        event.status === 'ESCALATED'
          ? 'bg-red-700 text-white ring-1 ring-red-500/80 animate-pulse'
          : 'bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/50',
      );
    }

    return badges;
  });

  protected readonly riskToneById = computed(() => {
    const tones = new Map<string, string>();

    for (const event of this.events()) {
      if (event.risk_score >= 75) {
        tones.set(event.id, 'text-red-400 font-semibold');
      } else if (event.risk_score >= 40) {
        tones.set(event.id, 'text-amber-300 font-medium');
      } else {
        tones.set(event.id, 'text-emerald-300');
      }
    }

    return tones;
  });

  protected selectEvent(event: TelemetryEvent): void {
    this.selectedEventId.set(event.id);
  }

  protected closeDetail(): void {
    this.selectedEventId.set(null);
  }

  protected trackByEventId(_index: number, event: TelemetryEvent): string {
    return event.id;
  }

  protected rowClasses(event: TelemetryEvent): string {
    return (
      this.rowToneById().get(event.id) ??
      'bg-slate-900/70 hover:bg-slate-800/80 border-l-4 border-transparent'
    );
  }

  protected statusBadgeClasses(event: TelemetryEvent): string {
    return (
      this.statusBadgeById().get(event.id) ??
      'bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/50'
    );
  }

  protected riskScoreClasses(event: TelemetryEvent): string {
    return this.riskToneById().get(event.id) ?? 'text-emerald-300';
  }
}
