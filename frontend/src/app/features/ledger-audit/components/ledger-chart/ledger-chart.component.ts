import { Component, computed, input } from '@angular/core';

import { TelemetryEvent } from '../../../../core/models/telemetry-event.model';

interface ChartPoint {
  x: number;
  y: number;
  event: TelemetryEvent;
  isSpike: boolean;
}

interface ChartModel {
  width: number;
  height: number;
  linePath: string;
  areaPath: string;
  points: ChartPoint[];
  yTicks: { y: number; label: string }[];
  xLabels: { x: number; label: string }[];
  maxAmount: number;
}

const CHART_WIDTH = 960;
const CHART_HEIGHT = 300;
const SPIKE_THRESHOLD = 10_000;

@Component({
  selector: 'app-ledger-chart',
  templateUrl: './ledger-chart.component.html',
})
export class LedgerChartComponent {
  readonly events = input.required<readonly TelemetryEvent[]>();

  protected readonly chart = computed<ChartModel | null>(() => {
    const snapshot = this.events();
    if (!snapshot.length) {
      return null;
    }

    const chronological = [...snapshot].sort(
      (left, right) =>
        new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime(),
    );

    const padding = { top: 24, right: 24, bottom: 36, left: 56 };
    const innerWidth = CHART_WIDTH - padding.left - padding.right;
    const innerHeight = CHART_HEIGHT - padding.top - padding.bottom;
    const maxAmount = Math.max(
      ...chronological.map((event) => event.transaction_amount),
      SPIKE_THRESHOLD,
    );

    const points: ChartPoint[] = chronological.map((event, index) => {
      const xRatio =
        chronological.length === 1 ? 0.5 : index / (chronological.length - 1);

      return {
        x: padding.left + xRatio * innerWidth,
        y:
          padding.top +
          innerHeight -
          (event.transaction_amount / maxAmount) * innerHeight,
        event,
        isSpike: event.transaction_amount > SPIKE_THRESHOLD,
      };
    });

    const linePath = points
      .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
      .join(' ');

    const baseline = padding.top + innerHeight;
    const areaPath = `${linePath} L ${points[points.length - 1].x} ${baseline} L ${points[0].x} ${baseline} Z`;

    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
      const amount = maxAmount * ratio;
      return {
        y: padding.top + innerHeight - ratio * innerHeight,
        label: this.formatCurrency(amount),
      };
    });

    const xLabelIndexes = this.pickLabelIndexes(chronological.length);
    const xLabels = xLabelIndexes.map((index) => ({
      x: points[index].x,
      label: this.formatTime(chronological[index].timestamp),
    }));

    return {
      width: CHART_WIDTH,
      height: CHART_HEIGHT,
      linePath,
      areaPath,
      points,
      yTicks,
      xLabels,
      maxAmount,
    };
  });

  protected readonly hasData = computed(() => this.events().length > 0);

  private pickLabelIndexes(length: number): number[] {
    if (length <= 1) {
      return [0];
    }

    if (length <= 4) {
      return Array.from({ length }, (_, index) => index);
    }

    const lastIndex = length - 1;
    return [0, Math.floor(lastIndex / 2), lastIndex];
  }

  private formatCurrency(amount: number): string {
    if (amount >= 1_000_000) {
      return `$${(amount / 1_000_000).toFixed(1)}M`;
    }

    if (amount >= 1_000) {
      return `$${(amount / 1_000).toFixed(0)}k`;
    }

    return `$${Math.round(amount)}`;
  }

  private formatTime(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }
}
