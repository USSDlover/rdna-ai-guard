import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { TelemetryStateService } from '../../core/services/telemetry-state.service';
import { GlobalThreatToastComponent } from '../../shared/components/global-threat-toast/global-threat-toast.component';

interface NavItem {
  label: string;
  route: string;
  description: string;
  enabled: boolean;
}

@Component({
  selector: 'app-dashboard-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, GlobalThreatToastComponent],
  templateUrl: './dashboard-shell.component.html',
  styleUrl: './dashboard-shell.component.css',
})
export class DashboardShellComponent {
  /** Eagerly attach the shared telemetry buffer for all child dashboard routes. */
  private readonly telemetryState = inject(TelemetryStateService);

  protected readonly navItems = signal<NavItem[]>([
    {
      label: 'Cyber Grid Security',
      route: '/dashboard/cyber-grid',
      description: 'Live SSE threat matrix',
      enabled: true,
    },
    {
      label: 'Financial Ledger Audit',
      route: '/dashboard/ledger-audit',
      description: 'Fraud syndicate tracing',
      enabled: true,
    },
  ]);

  protected readonly topStats = signal([
    { label: 'Ingestion Gate', value: 'ONLINE', tone: 'text-emerald-400' },
    { label: 'Ollama Bridge', value: 'ACTIVE', tone: 'text-cyan-400' },
    { label: 'Cloud Mesh', value: 'STANDBY', tone: 'text-amber-300' },
  ]);
}
