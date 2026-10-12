// Mirrors app/schemas/*.py from the backend. Kept as a single hand-written
// file rather than codegen (e.g. openapi-typescript) for this step — flagged
// as a Step 11 improvement: generating this from the live OpenAPI schema
// would eliminate drift risk between backend and frontend types entirely.

export type UUID = string;

// --- Enums (mirrors app/models/enums.py) ---
export type RepositorySourceType = "zip_upload" | "github_public" | "github_private_oauth";
export type RepositoryStatus = "pending" | "scanning" | "parsing" | "embedding" | "ready" | "failed";
export type ProgrammingLanguage = "python" | "javascript" | "typescript" | "java" | "cpp" | "go" | "unknown";
export type FileIndexStatus = "pending" | "indexed" | "stale" | "excluded";
export type DocumentType =
  | "readme" | "installation_guide" | "setup_guide" | "folder_structure"
  | "api_docs" | "class_docs" | "function_docs" | "architecture_docs"
  | "database_docs" | "deployment_guide" | "contribution_guide" | "faq" | "diagram";
export type DocumentStatus = "generating" | "complete" | "failed" | "stale";
export type TaskType =
  | "repository_ingestion" | "full_documentation_generation"
  | "incremental_regeneration" | "documentation_review" | "export";
export type TaskStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled" | "retrying";
export type MessageRole = "user" | "assistant" | "system";
export type ExportFormat = "markdown" | "html" | "pdf";

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  readme: "README",
  installation_guide: "Installation Guide",
  setup_guide: "Setup Guide",
  folder_structure: "Folder Structure",
  api_docs: "API Documentation",
  class_docs: "Class Documentation",
  function_docs: "Function Documentation",
  architecture_docs: "Architecture",
  database_docs: "Database",
  deployment_guide: "Deployment Guide",
  contribution_guide: "Contribution Guide",
  faq: "FAQ",
  diagram: "Diagrams",
};

// --- User / Auth ---
export interface User {
  id: UUID;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  github_username: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// --- Project ---
export interface Project {
  id: UUID;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  repository_count: number;
}

// --- Repository ---
export interface Repository {
  id: UUID;
  project_id: UUID;
  source_type: RepositorySourceType;
  github_url: string | null;
  default_branch: string | null;
  latest_commit_hash: string | null;
  status: RepositoryStatus;
  status_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface RepositoryFile {
  id: UUID;
  file_path: string;
  language: ProgrammingLanguage;
  size_bytes: number;
  index_status: FileIndexStatus;
}

// --- Documentation ---
export interface ReviewIssue {
  type: string;
  location: string | null;
  severity: "low" | "medium" | "high";
  description: string;
}

export interface ReviewResult {
  id: UUID;
  quality_score: number;
  issues: ReviewIssue[];
  created_at: string;
}

export interface GeneratedDocument {
  id: UUID;
  doc_type: DocumentType;
  content: string;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  review_result: ReviewResult | null;
}

export interface GeneratedDocumentSummary {
  id: UUID;
  doc_type: DocumentType;
  status: DocumentStatus;
  updated_at: string;
}

export interface DocumentationVersion {
  id: UUID;
  version_number: number;
  commit_hash: string;
  is_current: boolean;
  created_at: string;
  documents: GeneratedDocumentSummary[];
}

// --- Chat ---
export interface Citation {
  file_path: string;
  start_line: number | null;
  end_line: number | null;
  similarity_score: number;
}

export interface ChatMessage {
  id: UUID;
  role: MessageRole;
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface Chat {
  id: UUID;
  repository_id: UUID;
  title: string | null;
  created_at: string;
  updated_at: string;
}

// --- Task ---
export interface Task {
  id: UUID;
  task_type: TaskType;
  status: TaskStatus;
  progress: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// --- Pagination envelope (mirrors app/schemas/common.py) ---
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
