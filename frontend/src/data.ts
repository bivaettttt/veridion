export type Project = {
  id: string;
  name: string;
  description: string;
  role: string;
  lab: boolean;
};
export type User = {
  id: string;
  name: string;
  email: string;
  is_admin: boolean;
};
export type Source = {
  id: string;
  title: string;
  category: string;
  version: number | null;
  archived_at: string | null;
};
export type Version = {
  version: number;
  content_hash: string;
  filename: string;
  created_at: string;
  normalized: string;
};
export type Hit = {
  chunk_id: string;
  source_id: string;
  version_id: string;
  version: number;
  title: string;
  category: string;
  content: string;
  heading: string;
  page: number | null;
  start_at: number;
  end_at: number;
  score: number;
};
export type Fact = {
  property: string;
  value: string;
  unit: string;
  modality: string;
  context: string;
  text: string;
  chunk_id: string;
};
export type Citation = {
  id: string;
  chunk_id: string;
  source_id: string;
  title: string;
  version: number;
  version_id: string;
  heading: string;
  page: number | null;
  content_hash: string;
  quote: string;
  start_at: number;
  end_at: number;
  original_url: string;
  integrity: string;
  freshness: string;
};
export type Answer = {
  id: string;
  query: string;
  provider: string;
  model: string;
  created_at: string;
  output: {
    summary: string;
    assessment: string;
    claims: { text: string; reason: string; evidence: Fact[] }[];
    contradictions: { type: string; reason: string; left: Fact; right: Fact }[];
    generation?: {
      status: string;
      candidate?: string;
      citation_chunks: string[];
    };
  };
  citations: Citation[];
  context: Hit[];
  reviews: {
    id: string;
    decision: string;
    rationale: string;
    author: string;
  }[];
};
export type AnswerItem = {
  id: string;
  query: string;
  assessment: string;
  decision: string;
  created_at: string;
};
export type Eval = {
  id: string;
  configuration: { mode: string; provider: string; dataset: string };
  results: {
    metrics: Record<string, number | null>;
    cases: {
      case: string;
      question: string;
      answer_id: string;
      correct: boolean;
      expected: string;
      actual: string;
      recall: number;
      valid: number;
      citations: number;
      sources: string[];
    }[];
  };
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function call<T>(
  path: string,
  body?: unknown,
  method = body === undefined ? "GET" : "POST",
): Promise<T> {
  const headers = new Headers({ "X-Veridion-Client": "1" });
  if (body !== undefined && !(body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const res = await fetch("/api/v1" + path, {
    method,
    headers,
    body:
      body instanceof FormData
        ? body
        : body === undefined
          ? undefined
          : JSON.stringify(body),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => null);
    throw new ApiError(error?.error?.message || "Request failed", res.status);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}
export const label = (value: string) =>
  ({
    INSUFFICIENT_EVIDENCE: "Insufficient evidence",
    SUPPORTED_BY_SOURCES: "Supported by sources",
    CONTRADICTED_BY_SOURCES: "Contradicted by sources",
    MIXED_EVIDENCE: "Mixed evidence",
    POTENTIAL_CONFLICT: "Potential conflict",
    DIFFERENT_MODALITY: "Different modalities",
    DIFFERENT_CONTEXT: "Different contexts",
    NEEDS_CONTEXT: "Context missing",
    VALID: "Verified citation",
    AUTO_ASSESSED: "Automatically assessed",
    IN_REVIEW: "In review",
    REQUIRES_REVIEW: "Requires review",
    CURRENT: "Current version",
    HISTORICAL: "Historical version",
  })[value] ?? value.toLowerCase().replaceAll("_", " ");
export const date = (value: string) =>
  new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(
    new Date(value),
  );

export type LabRun = {
  id: string;
  results: {
    scenario: string;
    passed: boolean;
    observed: unknown;
    sources: string[];
    expectation: string;
  }[];
};
