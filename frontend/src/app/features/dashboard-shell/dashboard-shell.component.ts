import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

interface NavItem {
  label: string;
  route: string;
  description: string;
  enabled: boolean;
}

@Component({
  selector: 'app-dashboard-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './dashboard-shell.component.html',
  styleUrl: './dashboard-shell.component.css',
})
export class DashboardShellComponent {
  protected readonly navItems = signal<NavItem[]>([
    {
      label: 'Cyber Grid Security',
      route: '/dashboard/cyber-grid',
      description: 'Live SSE threat matrix',
      enabled: true,
    },
    {
      label: 'Financial Ledger Audit',
      route: '/dashboard/financial-ledger',
      description: 'Fraud syndicate tracing',
      enabled: false,
    },
  ]);

  protected readonly topStats = signal([
    { label: 'Ingestion Gate', value: 'ONLINE', tone: 'text-emerald-400' },
    { label: 'Ollama Bridge', value: 'ACTIVE', tone: 'text-cyan-400' },
    { label: 'Cloud Mesh', value: 'STANDBY', tone: 'text-amber-300' },
  ]);
}
