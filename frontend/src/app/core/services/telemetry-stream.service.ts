import { DestroyRef, Injectable, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Observable, Subject } from 'rxjs';

import { TelemetryEvent } from '../models/telemetry-event.model';

const TELEMETRY_STREAM_URL = 'http://127.0.0.1:8000/api/v1/telemetry/stream';

@Injectable({ providedIn: 'root' })
export class TelemetryStreamService {
  private readonly destroyRef = inject(DestroyRef);
  private readonly telemetrySubject = new Subject<TelemetryEvent>();
  private eventSource: EventSource | null = null;

  readonly telemetry$: Observable<TelemetryEvent> = this.telemetrySubject.asObservable();

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

  streamForLifecycle(): Observable<TelemetryEvent> {
    return this.telemetry$.pipe(takeUntilDestroyed(this.destroyRef));
  }
}
