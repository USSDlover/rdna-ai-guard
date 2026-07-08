import { DOCUMENT } from '@angular/common';
import {
  Component,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

import { TelemetryEvent } from '../../../../core/models/telemetry-event.model';

@Component({
  selector: 'app-telemetry-detail-modal',
  templateUrl: './telemetry-detail-modal.component.html',
  styleUrl: './telemetry-detail-modal.component.css',
})
export class TelemetryDetailModalComponent {
  private readonly document = inject(DOCUMENT);
  private readonly sanitizer = inject(DomSanitizer);

  readonly event = input.required<TelemetryEvent | null>();

  readonly dismissed = output<void>();

  protected readonly highlightedJson = computed<SafeHtml>(() => {
    const selected = this.event();
    if (!selected) {
      return this.sanitizer.bypassSecurityTrustHtml('');
    }

    const formatted = JSON.stringify(selected, null, 2);
    return this.sanitizer.bypassSecurityTrustHtml(this.syntaxHighlight(formatted));
  });

  protected readonly statusTone = computed(() => {
    const selected = this.event();
    if (!selected) {
      return 'text-slate-300';
    }

    return selected.status === 'ESCALATED' ? 'text-red-300' : 'text-emerald-300';
  });

  private readonly escapeListenerAttached = signal(false);

  constructor() {
    effect(() => {
      const isOpen = this.event() !== null;

      if (isOpen && !this.escapeListenerAttached()) {
        this.document.addEventListener('keydown', this.onEscapeKey);
        this.escapeListenerAttached.set(true);
        return;
      }

      if (!isOpen && this.escapeListenerAttached()) {
        this.document.removeEventListener('keydown', this.onEscapeKey);
        this.escapeListenerAttached.set(false);
      }
    });
  }

  protected close(): void {
    this.dismissed.emit();
  }

  protected onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.close();
    }
  }

  private readonly onEscapeKey = (event: KeyboardEvent): void => {
    if (event.key === 'Escape') {
      this.close();
    }
  };

  private syntaxHighlight(json: string): string {
    const escaped = json
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    return escaped.replace(
      /("(\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (match) => {
        let className = 'json-number';

        if (/^"/.test(match)) {
          className = /:$/.test(match) ? 'json-key' : 'json-string';
        } else if (/true|false/.test(match)) {
          className = 'json-boolean';
        } else if (/null/.test(match)) {
          className = 'json-null';
        }

        return `<span class="${className}">${match}</span>`;
      },
    );
  }
}
