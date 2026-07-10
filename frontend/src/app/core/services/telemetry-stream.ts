import { Observable } from 'rxjs';

import { TelemetryEvent } from '../models/telemetry-event.model';

/**
 * DI contract for live SSE and mock telemetry producers.
 * Consumers inject this abstract class so Netlify mock builds can swap implementations.
 */
export abstract class TelemetryStream {
  abstract readonly telemetry$: Observable<TelemetryEvent>;
}
