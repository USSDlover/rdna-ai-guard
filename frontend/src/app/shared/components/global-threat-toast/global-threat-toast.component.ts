import { CurrencyPipe } from '@angular/common';
import { Component, computed, inject } from '@angular/core';

import { NotificationStateService } from '../../../core/services/notification-state.service';
import { TelemetryEvent } from '../../../core/models/telemetry-event.model';

@Component({
  selector: 'app-global-threat-toast',
  imports: [CurrencyPipe],
  templateUrl: './global-threat-toast.component.html',
  styleUrl: './global-threat-toast.component.css',
})
export class GlobalThreatToastComponent {
  protected readonly notificationState = inject(NotificationStateService);

  protected readonly activeAlerts = this.notificationState.activeAlerts;

  protected readonly vectorToneById = computed(() => {
    const tones = new Map<string, string>();

    for (const alert of this.activeAlerts()) {
      switch (alert.primary_vector) {
        case 'CYBER':
          tones.set(alert.id, 'bg-cyan-500/20 text-cyan-300 ring-cyan-500/40');
          break;
        case 'FRAUD':
          tones.set(alert.id, 'bg-amber-500/20 text-amber-300 ring-amber-500/40');
          break;
        default:
          tones.set(alert.id, 'bg-slate-700/60 text-slate-300 ring-slate-600/50');
      }
    }

    return tones;
  });

  protected vectorBadgeClasses(alert: TelemetryEvent): string {
    return (
      this.vectorToneById().get(alert.id) ??
      'bg-slate-700/60 text-slate-300 ring-slate-600/50'
    );
  }

  protected dismiss(alertId: string): void {
    this.notificationState.dismissAlert(alertId);
  }
}
