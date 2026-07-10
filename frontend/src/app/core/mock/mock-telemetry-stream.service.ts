import { DestroyRef, Injectable, inject } from '@angular/core';
import { ReplaySubject, interval } from 'rxjs';

import { TelemetryEvent } from '../models/telemetry-event.model';
import { TelemetryStream } from '../services/telemetry-stream';
import {
  MOCK_TELEMETRY_EVENTS,
  createMockTelemetryEvent,
} from './mock-telemetry.data';

const REPLAY_BUFFER_SIZE = 50;
const LIVE_TICK_MS = 3_500;

/**
 * Netlify / demo telemetry producer — no EventSource, no backend.
 * Seeds a FinSec corpus then emits synthetic live ticks.
 */
@Injectable()
export class MockTelemetryStreamService extends TelemetryStream {
  private readonly destroyRef = inject(DestroyRef);
  private readonly telemetrySubject = new ReplaySubject<TelemetryEvent>(REPLAY_BUFFER_SIZE);
  private sequence = 0;

  readonly telemetry$ = this.telemetrySubject.asObservable();

  constructor() {
    super();
    this.seedBaseline();
    this.startLiveTicker();
  }

  private seedBaseline(): void {
    for (const event of MOCK_TELEMETRY_EVENTS) {
      this.telemetrySubject.next(event);
    }
  }

  private startLiveTicker(): void {
    const subscription = interval(LIVE_TICK_MS).subscribe(() => {
      this.sequence += 1;
      this.telemetrySubject.next(createMockTelemetryEvent(this.sequence));
    });

    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }
}
