export type PrimaryVector = 'CYBER' | 'FRAUD' | 'NONE';
export type TelemetryStatus = 'PASSED' | 'ESCALATED';

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
}
