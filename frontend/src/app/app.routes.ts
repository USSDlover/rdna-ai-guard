import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full',
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard-shell/dashboard-shell.component').then(
        (m) => m.DashboardShellComponent,
      ),
    children: [
      {
        path: '',
        redirectTo: 'cyber-grid',
        pathMatch: 'full',
      },
      {
        path: 'cyber-grid',
        loadComponent: () =>
          import(
            './features/cyber-grid/components/cyber-grid-dashboard/cyber-grid-dashboard.component'
          ).then((m) => m.CyberGridDashboardComponent),
      },
      {
        path: 'ledger-audit',
        loadComponent: () =>
          import(
            './features/ledger-audit/components/ledger-dashboard/ledger-dashboard.component'
          ).then((m) => m.LedgerDashboardComponent),
      },
    ],
  },
];