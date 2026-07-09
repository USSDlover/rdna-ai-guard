import { Injectable, inject, signal } from '@angular/core';

import { TelemetryEvent } from '../models/telemetry-event.model';
import { TelemetryStreamService } from './telemetry-stream.service';

const MAX_EVENT_BUFFER = 50;

/**
 * Root-level telemetry buffer shared across all dashboard routes.
 * Survives navigation between cyber-grid and ledger-audit.
 */
@Injectable({ providedIn: 'root' })
export class TelemetryStateService {
  private readonly telemetryStream = inject(TelemetryStreamService);

  private readonly eventBuffer: TelemetryEvent[] = [];

  readonly events = signal<readonly TelemetryEvent[]>([]);

  constructor() {
    this.telemetryStream.telemetry$.subscribe((event) => {
      this.ingestEvent(event);
    });
  }

  private ingestEvent(event: TelemetryEvent): void {
    const existingIndex = this.eventBuffer.findIndex((item) => item.id === event.id);

    if (existingIndex >= 0) {
      this.eventBuffer[existingIndex] = event;
    } else {
      this.eventBuffer.unshift(event);
    }

    if (this.eventBuffer.length > MAX_EVENT_BUFFER) {
      this.eventBuffer.length = MAX_EVENT_BUFFER;
    }

    this.events.set(Object.freeze([...this.eventBuffer]));
  }
}
