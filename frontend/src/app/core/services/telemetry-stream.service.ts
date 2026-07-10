import { DestroyRef, Injectable, inject } from '@angular/core';
import { ReplaySubject } from 'rxjs';

import { environment } from '../../../environments/environment';
import { TelemetryEvent } from '../models/telemetry-event.model';
import { TelemetryStream } from './telemetry-stream';

const REPLAY_BUFFER_SIZE = 50;

/**
 * Live SSE telemetry producer against the FastAPI backend.
 */
@Injectable()
export class TelemetryStreamService extends TelemetryStream {
  private readonly destroyRef = inject(DestroyRef);
  private readonly telemetrySubject = new ReplaySubject<TelemetryEvent>(REPLAY_BUFFER_SIZE);
  private eventSource: EventSource | null = null;

  readonly telemetry$ = this.telemetrySubject.asObservable();

  constructor() {
    super();
    this.connect();
    this.destroyRef.onDestroy(() => this.disconnect());
  }

  private streamUrl(): string {
    const base = environment.apiUrl.replace(/\/$/, '');
    return `${base}/v1/telemetry/stream`;
  }

  private connect(): void {
    if (typeof EventSource === 'undefined') {
      return;
    }

    this.disconnect();

    this.eventSource = new EventSource(this.streamUrl());

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
