import { Component, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger' | 'neutral';

@Component({
  selector: 'app-status-pill',
  template: `
    <span
      class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold tracking-wide uppercase"
      [class]="toneClasses()"
    >
      {{ label() }}
    </span>
  `,
})
export class StatusPillComponent {
  readonly label = input.required<string>();
  readonly tone = input<StatusTone>('neutral');

  protected toneClasses(): string {
    switch (this.tone()) {
      case 'success':
        return 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/40';
      case 'warning':
        return 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/40';
      case 'danger':
        return 'bg-red-500/20 text-red-300 ring-1 ring-red-500/60';
      default:
        return 'bg-slate-700/60 text-slate-300 ring-1 ring-slate-600/50';
    }
  }
}
