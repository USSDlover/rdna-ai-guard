import { Component, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { TelemetryStreamService } from '../../../core/services/telemetry-stream.service';
import { TelemetryEvent } from '../../../core/models/telemetry-event.model';

@Component({
  selector: 'app-alert-banner',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './alert-banner.component.html',
  styleUrl: './alert-banner.component.css'
})
export class AlertBannerComponent implements OnInit, OnDestroy {
  alerts = signal<TelemetryEvent[]>([]);
  private sub!: Subscription;

  constructor(private telemetry: TelemetryStreamService) {}

  ngOnInit() {
    this.sub = this.telemetry.telemetry$.subscribe((event: TelemetryEvent) => {
      if (event.risk_score > 85) {
        this.alerts.update(current => [event, ...current].slice(0, 5));
        setTimeout(() => {
          this.alerts.update(current => current.filter(a => a.id !== event.id));
        }, 5000);
      }
    });
  }

  dismiss(id: string) {
    this.alerts.update(current => current.filter(a => a.id !== id));
  }

  ngOnDestroy() {
    this.sub.unsubscribe();
  }
}