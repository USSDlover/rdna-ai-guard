import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, inject, effect, viewChild, ElementRef } from '@angular/core';
import { Chart, registerables } from 'chart.js';

import { LedgerStateService } from '../../data-access/ledger-state.service';

Chart.register(...registerables);

@Component({
  selector: 'app-ledger-dashboard',
  imports: [CurrencyPipe, DatePipe],
  providers: [LedgerStateService],
  templateUrl: './ledger-dashboard.component.html',
  styleUrl: './ledger-dashboard.component.css',
})
export class LedgerDashboardComponent {
  protected readonly state = inject(LedgerStateService);

  private readonly barCanvas = viewChild<ElementRef<HTMLCanvasElement>>('barChart');
  private readonly pieCanvas = viewChild<ElementRef<HTMLCanvasElement>>('pieChart');

  private barChart: Chart | null = null;
  private pieChart: Chart | null = null;

  constructor() {
    effect(() => {
      const events = this.state.fraudEvents();
      this.updateBarChart(events);
      this.updatePieChart(events);
    });
  }

  private updateBarChart(events: any[]): void {
    const canvas = this.barCanvas()?.nativeElement;
    if (!canvas) return;

    const labels = events.slice(0, 10).map((e) =>
      new Date(e.timestamp).toLocaleTimeString()
    );
    const amounts = events.slice(0, 10).map((e) => e.transaction_amount);

    if (this.barChart) {
      this.barChart.data.labels = labels;
      this.barChart.data.datasets[0].data = amounts;
      this.barChart.update();
      return;
    }

    this.barChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Fraud Amount (USD)',
          data: amounts,
          backgroundColor: 'rgba(239, 68, 68, 0.6)',
          borderColor: 'rgba(239, 68, 68, 1)',
          borderWidth: 1,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { labels: { color: '#94a3b8' } },
        },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
        },
      },
    });
  }

    private updatePieChart(events: any[]): void {
    const canvas = this.pieCanvas()?.nativeElement;
    if (!canvas) return;

    const escalated = events.filter(e => e.status === 'ESCALATED').length;
    const passed = events.filter(e => e.status === 'PASSED').length;

    const labels = ['ESCALATED', 'PASSED'];
    const data = [escalated, passed];

    if (this.pieChart) {
      this.pieChart.data.labels = labels;
      this.pieChart.data.datasets[0].data = data;
      this.pieChart.update();
      return;
    }

    this.pieChart = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: [
            'rgba(239, 68, 68, 0.7)',
            'rgba(16, 185, 129, 0.7)',
          ],
          borderColor: [
            'rgba(239, 68, 68, 1)',
            'rgba(16, 185, 129, 1)',
          ],
          borderWidth: 1,
          }],
        },
        options: {
          responsive: true,
        plugins: {
          legend: { labels: { color: '#94a3b8' } },
          title: {
            display: true,
            text: 'Escalated vs Passed',
            color: '#94a3b8',
          }
        },
      },
    });
  }
}