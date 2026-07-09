export type PrimaryVector = 'CYBER' | 'FRAUD' | 'NONE';
export type TelemetryStatus = 'PASSED' | 'ESCALATED';

export interface CloudEscalation {
  provider?: string;
  model?: string;
  cyber_analysis?: string;
  cyber_score?: number;
  fraud_analysis?: string;
  fraud_score?: number;
  synthesized_narrative?: string;
}

export interface TelemetryPayloadMetadata {
  source_ip?: string;
  request_path?: string;
  transaction_amount?: number;
  account_token?: string;
  cloud_escalation?: CloudEscalation;
  [key: string]: unknown;
}

export interface TelemetryEvent {
  id: string;
  timestamp: string;
  source_ip: string;
  request_path: string;
  transaction_amount: number;
  account_token: string;
  risk_score: number;
  primary_vector: PrimaryVector;
  status: TelemetryStatus;
  payload_metadata?: TelemetryPayloadMetadata | null;
  triage_narrative?: string | null;
}
