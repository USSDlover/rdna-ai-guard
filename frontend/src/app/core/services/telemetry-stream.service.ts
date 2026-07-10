import { DestroyRef, Injectable, inject } from '@angular/core';
import { ReplaySubject } from 'rxjs';

import { TelemetryEvent } from '../models/telemetry-event.model';

// Relative path so the SPA works on the unified FastAPI origin (and via ng serve proxy).
const TELEMETRY_STREAM_URL = '/api/v1/telemetry/stream';
const REPLAY_BUFFER_SIZE = 50;

@Injectable({ providedIn: 'root' })
export class TelemetryStreamService {
  private readonly destroyRef = inject(DestroyRef);
  private readonly telemetrySubject = new ReplaySubject<TelemetryEvent>(REPLAY_BUFFER_SIZE);
  private eventSource: EventSource | null = null;

  readonly telemetry$ = this.telemetrySubject.asObservable();

  constructor() {
    this.connect();

    this.destroyRef.onDestroy(() => this.disconnect());
  }

  private connect(): void {
    if (typeof EventSource === 'undefined') {
      return;
    }

    this.disconnect();

    this.eventSource = new EventSource(TELEMETRY_STREAM_URL);

    this.eventSource.addEventListener('telemetry', (message: MessageEvent<string>) => {
      try {
        const event = JSON.parse(message.data) as TelemetryEvent;
        this.telemetrySubject.next(event);
      } catch {
        // Malformed SSE payloads are ignored to keep the stream resilient.
      }
    });

    this.eventSource.onerror = () => {
      this.disconnect();
      window.setTimeout(() => this.connect(), 3000);
    };
  }

  private disconnect(): void {
    this.eventSource?.close();
    this.eventSource = null;
  }
}
