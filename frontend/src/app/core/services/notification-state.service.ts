import { Injectable, inject, signal } from '@angular/core';

import { TelemetryEvent } from '../models/telemetry-event.model';
import { TelemetryStream } from './telemetry-stream';

const HIGH_RISK_THRESHOLD = 85;
const AUTO_DISMISS_MS = 6_000;

@Injectable({ providedIn: 'root' })
export class NotificationStateService {
  private readonly telemetryStream = inject(TelemetryStream);

  private readonly dismissTimers = new Map<string, ReturnType<typeof setTimeout>>();

  readonly activeAlerts = signal<readonly TelemetryEvent[]>([]);

  constructor() {
    this.telemetryStream.telemetry$.subscribe((event) => {
      if (event.risk_score > HIGH_RISK_THRESHOLD) {
        this.raiseAlert(event);
      }
    });
  }

  dismissAlert(id: string): void {
    const timer = this.dismissTimers.get(id);
    if (timer) {
      clearTimeout(timer);
      this.dismissTimers.delete(id);
    }

    this.activeAlerts.update((alerts) => alerts.filter((alert) => alert.id !== id));
  }

  clearAll(): void {
    for (const timer of this.dismissTimers.values()) {
      clearTimeout(timer);
    }

    this.dismissTimers.clear();
    this.activeAlerts.set([]);
  }

  private raiseAlert(event: TelemetryEvent): void {
    this.activeAlerts.update((alerts) => {
      if (alerts.some((alert) => alert.id === event.id)) {
        return alerts;
      }

      return [...alerts, event];
    });

    this.scheduleAutoDismiss(event.id);
  }

  private scheduleAutoDismiss(id: string): void {
    const existingTimer = this.dismissTimers.get(id);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    const timer = setTimeout(() => {
      this.dismissAlert(id);
    }, AUTO_DISMISS_MS);

    this.dismissTimers.set(id, timer);
  }
}
