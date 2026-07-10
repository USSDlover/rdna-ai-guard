import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';

import { environment } from '../environments/environment';
import { routes } from './app.routes';
import { MockTelemetryStreamService } from './core/mock/mock-telemetry-stream.service';
import { TelemetryStream } from './core/services/telemetry-stream';
import { TelemetryStreamService } from './core/services/telemetry-stream.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    {
      provide: TelemetryStream,
      useClass: environment.useMockData
        ? MockTelemetryStreamService
        : TelemetryStreamService,
    },
  ],
};
