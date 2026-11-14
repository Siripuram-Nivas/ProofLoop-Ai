export type Verdict =
  | "supported"
  | "contradicted"
  | "mixed"
  | "insufficient"
  | "outdated"
  | "unverified"
  | "inconclusive";

export type Relationship = "supports" | "contradicts" | "insufficient";

export interface User {
  id: string;
  email: string | null;
  is_guest: boolean;
  created_at: string;
}

export interface Stage {
  key: string;
  label: string;
  status: "pending" | "active" | "done" | "failed" | "partial";
  detail: string;
  at: string | null;
}

export interface NumberPair {
  claim_value: number;
  evidence_value: number;
  relative_diff?: number;
  kind: "match" | "near" | "mismatch";
}

export interface YearPair {
  claim_value: number;
  evidence_value: number;
  kind: "match" | "near" | "mismatch";
}

export interface Evidence {
  id: string;
  claim_id: string;
  source_id: string;
  source_title: string;
  source_url: string;
  source_type: string;
  quality: string;
  excerpt: string;
  relationship: Relationship;
  match_kind: string;
  explanation: string;
  matched_terms: string[];
  relevance: number;
  numbers: NumberPair[];
  years: YearPair[];
  retrieved_at: string;
  source_updated_at: string | null;
  stale: boolean;
}

export interface Claim {
  id: string;
  text: string;
  original_span: string;
  category: string;
  entities: string[];
  numbers: number[];
  dates: string[];
  confidence: number;
  verdict: Verdict;
  verdict_basis: string;
  evidence: Evidence[];
  research_failed: boolean;
  manual?: boolean;
}

export interface Source {
  id: string;
  title: string;
  url: string;
  publisher: string;
  source_type: string;
  published_at: string | null;
  updated_at: string | null;
  retrieved_at: string;
  quality: string;
  quality_note: string;
  stale: boolean;
}

export interface Contradiction {
  id: string;
  claim_id: string;
  claim_text: string;
  kind: "numeric_mismatch" | "date_mismatch" | "source_disagreement";
  severity: "high" | "medium";
  summary: string;
  evidence_ids: string[];
}

export interface ReportEvidence {
  id: string;
  relationship: Relationship;
  excerpt: string;
  explanation: string;
  source_title: string;
  source_url: string;
  source_type: string;
  quality: string;
  retrieved_at: string;
  source_updated_at: string | null;
  stale: boolean;
}

export interface ReportClaim {
  id: string;
  text: string;
  category: string;
  verdict: Verdict;
  verdict_label: string;
  verdict_basis: string;
  confidence: number;
  confidence_kind: string;
  evidence: ReportEvidence[];
  conflicts: { id: string; kind: string; severity: string; summary: string }[];
}

export interface Report {
  verification_id: string;
  title: string;
  generated_at: string;
  input_kind: string;
  input_text: string | null;
  input_url: string | null;
  engine: { extraction: string; research: string };
  summary: {
    claims: number;
    supported: number;
    contradicted: number;
    mixed: number;
    insufficient: number;
    outdated: number;
    unverified: number;
    inconclusive: number;
    sources: number;
    conflicts: number;
  };
  claims: ReportClaim[];
  sources: Source[];
  contradictions: Contradiction[];
  limitations: string[];
  methodology: string[];
  disclaimer: string;
}

export interface AiProviderEvent {
  stage: string;
  provider: string;
  outcome: string;
  code: string | null;
}

export interface AiSection {
  engine: string | null;
  provider?: string | null;
  error?: { code: string; message: string } | null;
  outcome_unknown?: boolean;
  skipped?: string;
}

export interface AiInfo {
  provider: string | null;
  notices: string[];
  events: AiProviderEvent[];
  analysis: AiSection;
  review: AiSection;
  second_review: AiSection;
  error?: string;
}

export interface VerificationJob {
  id: string;
  title: string;
  input_kind: string;
  input_text: string | null;
  input_url: string | null;
  status: "queued" | "extracting" | "researching" | "evaluating" | "completed" | "failed";
  error: string | null;
  created_at: string;
  updated_at: string;
  engine: { extraction: string; research: string };
  ai?: AiInfo | null;
  stages: Stage[];
  claims: Claim[];
  sources: Source[];
  contradictions: Contradiction[];
  report: Report | null;
}

export interface VerificationSummary {
  id: string;
  title: string;
  status: VerificationJob["status"];
  input_kind: string;
  created_at: string;
  updated_at: string;
  claim_count: number;
  verdicts: Record<Verdict, number>;
  source_count: number;
  conflict_count: number;
  error: string | null;
}

export interface GraphNode {
  id: string;
  kind: "claim" | "evidence" | "source";
  label: string;
  verdict?: Verdict;
  category?: string;
  evidenceCount?: number;
  relationship?: Relationship;
  sourceTitle?: string;
  sourceUrl?: string;
  matchKind?: string;
  stale?: boolean;
  url?: string;
  sourceType?: string;
  quality?: string;
  retrievedAt?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  kind: Relationship | "derived_from";
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Stats {
  totals: {
    runs: number;
    claims: number;
    supported: number;
    contradicted: number;
    mixed: number;
    insufficient: number;
    outdated: number;
    unverified: number;
    inconclusive: number;
    unverified_all: number;
    sources: number;
    conflicts: number;
  };
  recent: VerificationSummary[];
  conflicts: {
    verification_id: string;
    verification_title: string;
    claim_id: string;
    kind: string;
    severity: string;
    summary: string;
  }[];
  latest_report: {
    verification_id: string;
    title: string;
    generated_at: string;
    summary: Report["summary"];
  } | null;
}

export interface HealthInfo {
  status: string;
  service: string;
  version: string;
  storage: string;
  research: string;
  extraction: string;
  image_ocr: boolean;
  environment: string;
}

export interface UploadResult {
  id: string;
  filename: string;
  kind: string;
  chars: number;
  preview: string;
}
