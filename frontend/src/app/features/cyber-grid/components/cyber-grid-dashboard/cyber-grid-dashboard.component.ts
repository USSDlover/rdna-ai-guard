import { Component, inject } from '@angular/core';

import { CyberStateService } from '../../data-access/cyber-state.service';
import { TelemetryTableComponent } from '../telemetry-table/telemetry-table.component';

@Component({
  selector: 'app-cyber-grid-dashboard',
  imports: [TelemetryTableComponent],
  providers: [CyberStateService],
  templateUrl: './cyber-grid-dashboard.component.html',
  styleUrl: './cyber-grid-dashboard.component.css',
})
export class CyberGridDashboardComponent {
  protected readonly state = inject(CyberStateService);
}
