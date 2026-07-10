import { TelemetryEvent } from '../models/telemetry-event.model';

/** Static FinSec demo corpus for Netlify mock builds (no backend). */
export const MOCK_TELEMETRY_EVENTS: readonly TelemetryEvent[] = [
  {
    id: 'mock-cyber-001',
    timestamp: new Date(Date.now() - 120_000).toISOString(),
    source_ip: '185.220.101.42',
    request_path: '/api/v1/auth/session',
    transaction_amount: 0,
    account_token: 'acct_ops_north',
    risk_score: 91,
    primary_vector: 'CYBER',
    status: 'ESCALATED',
    triage_narrative:
      'Local Gemma triage flagged anomalous header injection and credential stuffing velocity from a Tor exit node.',
    payload_metadata: {
      source_ip: '185.220.101.42',
      request_path: '/api/v1/auth/session',
      user_agent: 'python-requests/2.32.0',
      cloud_escalation: {
        provider: 'fireworks',
        model: 'accounts/fireworks/models/llama-v3p1-70b-instruct',
        cyber_analysis:
          'Packet-level anomalies: forged X-Forwarded-For chain, JWT alg=none probe, and burst login attempts across 14 accounts.',
        cyber_score: 94,
        fraud_analysis:
          'No wire-transfer pattern detected; activity is infrastructure abuse rather than ledger fraud.',
        fraud_score: 22,
        synthesized_narrative:
          'Cross-silo verdict: high-confidence cyber exploit. Recommend temporary IP block and forced MFA reset for targeted accounts.',
      },
    },
  },
  {
    id: 'mock-fraud-001',
    timestamp: new Date(Date.now() - 90_000).toISOString(),
    source_ip: '102.89.23.11',
    request_path: '/api/v1/payments/wire',
    transaction_amount: 48_750,
    account_token: 'acct_mule_lagos_7',
    risk_score: 88,
    primary_vector: 'FRAUD',
    status: 'ESCALATED',
    triage_narrative:
      'Structuring loop detected: three sub-$10k wires within 11 minutes toward a newly linked beneficiary.',
    payload_metadata: {
      source_ip: '102.89.23.11',
      request_path: '/api/v1/payments/wire',
      transaction_amount: 48_750,
      account_token: 'acct_mule_lagos_7',
      beneficiary_country: 'NG',
      cloud_escalation: {
        provider: 'fireworks',
        model: 'accounts/fireworks/models/llama-v3p1-70b-instruct',
        cyber_analysis:
          'TLS fingerprint matches prior clean mobile client; no exploit signatures in request headers.',
        cyber_score: 18,
        fraud_analysis:
          'Classic mule-account velocity: rapid beneficiary onboarding, cross-border hop, and amount just under reporting thresholds.',
        fraud_score: 93,
        synthesized_narrative:
          'Cross-silo verdict: synthetic fraud syndicate pattern. Hold settlement and escalate to AML review queue.',
      },
    },
  },
  {
    id: 'mock-toast-001',
    timestamp: new Date(Date.now() - 60_000).toISOString(),
    source_ip: '45.33.32.156',
    request_path: '/api/v1/ledger/transfer',
    transaction_amount: 125_000,
    account_token: 'acct_vip_dubai',
    risk_score: 97,
    primary_vector: 'FRAUD',
    status: 'ESCALATED',
    triage_narrative:
      'Critical risk: high-value outbound transfer with impossible travel (login geo vs beneficiary bank).',
    payload_metadata: {
      source_ip: '45.33.32.156',
      request_path: '/api/v1/ledger/transfer',
      transaction_amount: 125_000,
      account_token: 'acct_vip_dubai',
      cloud_escalation: {
        provider: 'fireworks',
        cyber_analysis: 'Session token reuse from two ASNs within 4 minutes — possible session hijack.',
        cyber_score: 81,
        fraud_analysis: 'Catastrophic ledger risk: $125k wire + new device + new beneficiary.',
        fraud_score: 98,
        synthesized_narrative:
          'Dual-vector crisis. Freeze account, revoke sessions, and page the FinSec on-call rotation.',
      },
    },
  },
  {
    id: 'mock-pass-001',
    timestamp: new Date(Date.now() - 45_000).toISOString(),
    source_ip: '10.0.12.44',
    request_path: '/api/v1/accounts/balance',
    transaction_amount: 0,
    account_token: 'acct_retail_042',
    risk_score: 12,
    primary_vector: 'NONE',
    status: 'PASSED',
    triage_narrative: 'Routine balance inquiry from known corporate VPN. Zero-token local triage.',
    payload_metadata: {
      source_ip: '10.0.12.44',
      request_path: '/api/v1/accounts/balance',
      account_token: 'acct_retail_042',
    },
  },
  {
    id: 'mock-cyber-002',
    timestamp: new Date(Date.now() - 30_000).toISOString(),
    source_ip: '203.0.113.88',
    request_path: '/api/v1/admin/export',
    transaction_amount: 0,
    account_token: 'acct_contractor_temp',
    risk_score: 76,
    primary_vector: 'CYBER',
    status: 'ESCALATED',
    triage_narrative:
      'Sensitive export endpoint hit outside change window with elevated role claim mismatch.',
    payload_metadata: {
      source_ip: '203.0.113.88',
      request_path: '/api/v1/admin/export',
      account_token: 'acct_contractor_temp',
      cloud_escalation: {
        provider: 'mock',
        cyber_analysis: 'Privilege-escalation attempt via stale contractor JWT and path traversal in export filter.',
        cyber_score: 79,
        fraud_analysis: 'No monetary movement; cyber-only vector.',
        fraud_score: 8,
        synthesized_narrative: 'Contain contractor identity and rotate export API keys.',
      },
    },
  },
  {
    id: 'mock-fraud-002',
    timestamp: new Date(Date.now() - 15_000).toISOString(),
    source_ip: '198.51.100.23',
    request_path: '/api/v1/payments/ach',
    transaction_amount: 9_850,
    account_token: 'acct_smurf_03',
    risk_score: 64,
    primary_vector: 'FRAUD',
    status: 'PASSED',
    triage_narrative:
      'Near-threshold ACH batch; local model kept PASSED with elevated watchlist tagging.',
    payload_metadata: {
      source_ip: '198.51.100.23',
      request_path: '/api/v1/payments/ach',
      transaction_amount: 9_850,
      account_token: 'acct_smurf_03',
    },
  },
  {
    id: 'mock-pass-002',
    timestamp: new Date(Date.now() - 8_000).toISOString(),
    source_ip: '10.0.8.19',
    request_path: '/api/v1/cards/authorize',
    transaction_amount: 42.5,
    account_token: 'acct_retail_108',
    risk_score: 8,
    primary_vector: 'NONE',
    status: 'PASSED',
    triage_narrative: 'Low-value POS authorization within historical spend envelope.',
    payload_metadata: {
      source_ip: '10.0.8.19',
      request_path: '/api/v1/cards/authorize',
      transaction_amount: 42.5,
      account_token: 'acct_retail_108',
    },
  },
  {
    id: 'mock-cyber-003',
    timestamp: new Date(Date.now() - 3_000).toISOString(),
    source_ip: '91.219.237.9',
    request_path: '/api/v1/webhooks/ingest',
    transaction_amount: 0,
    account_token: 'svc_partner_feed',
    risk_score: 83,
    primary_vector: 'CYBER',
    status: 'ESCALATED',
    triage_narrative:
      'Webhook replay storm with stale HMAC signatures — possible partner-key compromise.',
    payload_metadata: {
      source_ip: '91.219.237.9',
      request_path: '/api/v1/webhooks/ingest',
      account_token: 'svc_partner_feed',
      cloud_escalation: {
        provider: 'fireworks',
        cyber_analysis: 'Replay window abuse and nonce collision across 2.4k webhook deliveries.',
        cyber_score: 86,
        fraud_analysis: 'Downstream payment intents not yet mutated; preventative cyber hold.',
        fraud_score: 31,
        synthesized_narrative: 'Rotate partner HMAC secret and enable replay-cache enforcement.',
      },
    },
  },
];

const SOURCE_IPS = [
  '10.0.4.12',
  '172.16.9.44',
  '203.0.113.17',
  '198.51.100.91',
  '45.77.12.200',
] as const;

const PATHS = [
  '/api/v1/payments/wire',
  '/api/v1/auth/session',
  '/api/v1/ledger/transfer',
  '/api/v1/cards/authorize',
  '/api/v1/accounts/balance',
] as const;

/**
 * Builds a fresh pseudo-random telemetry event for the live mock ticker.
 */
export function createMockTelemetryEvent(sequence: number): TelemetryEvent {
  const roll = sequence % 5;
  const id = `mock-live-${Date.now()}-${sequence}`;
  const source_ip = SOURCE_IPS[sequence % SOURCE_IPS.length];
  const request_path = PATHS[sequence % PATHS.length];

  if (roll === 0) {
    return {
      id,
      timestamp: new Date().toISOString(),
      source_ip,
      request_path: '/api/v1/payments/wire',
      transaction_amount: 12_000 + (sequence % 7) * 3_500,
      account_token: `acct_demo_${sequence % 20}`,
      risk_score: 86 + (sequence % 10),
      primary_vector: 'FRAUD',
      status: 'ESCALATED',
      triage_narrative: 'Mock live ticker: high-velocity cross-border wire flagged for AML review.',
      payload_metadata: {
        source_ip,
        request_path: '/api/v1/payments/wire',
        cloud_escalation: {
          provider: 'mock',
          cyber_score: 20,
          fraud_score: 90,
          synthesized_narrative: 'Demo cloud mesh: fraud-dominant escalation.',
        },
      },
    };
  }

  if (roll === 1) {
    return {
      id,
      timestamp: new Date().toISOString(),
      source_ip,
      request_path: '/api/v1/auth/session',
      transaction_amount: 0,
      account_token: `acct_ops_${sequence % 9}`,
      risk_score: 78 + (sequence % 15),
      primary_vector: 'CYBER',
      status: 'ESCALATED',
      triage_narrative: 'Mock live ticker: exploit signature on auth edge.',
      payload_metadata: {
        source_ip,
        request_path: '/api/v1/auth/session',
        cloud_escalation: {
          provider: 'mock',
          cyber_score: 88,
          fraud_score: 15,
          synthesized_narrative: 'Demo cloud mesh: cyber-dominant escalation.',
        },
      },
    };
  }

  return {
    id,
    timestamp: new Date().toISOString(),
    source_ip,
    request_path,
    transaction_amount: sequence % 2 === 0 ? 0 : 25 + (sequence % 40),
    account_token: `acct_retail_${sequence % 50}`,
    risk_score: 5 + (sequence % 25),
    primary_vector: 'NONE',
    status: 'PASSED',
    triage_narrative: 'Mock live ticker: clean local triage (zero cloud tokens).',
    payload_metadata: {
      source_ip,
      request_path,
    },
  };
}
