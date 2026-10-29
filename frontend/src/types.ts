export interface RecordBase {
  id: string;
  created_at: string;
  updated_at: string;
}
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
export interface DatabaseTable {
  name: string;
  columns: string[];
  total: number;
}
export type DatabaseRecord = Record<string, unknown>;
export interface Student extends RecordBase {
  display_name: string;
  email: string;
  highest_level: string | null;
  ai_summary: string | null;
  context: Record<string, unknown>;
}
export interface Enrolment extends RecordBase {
  student_id: string;
  class_id: string;
  starts_on: string;
  ends_on: string | null;
  status: "active" | "ended" | "cancelled";
}
export interface StudentDetail extends Student {
  as_of: string;
  current_enrolments: Enrolment[];
  enrolment_history: Enrolment[];
}
export interface Term extends RecordBase {
  name: string;
  starts_on: string;
  ends_on: string;
}
export interface Location extends RecordBase {
  name: string;
  address: string;
  timezone: string;
}
export interface StudioClass extends RecordBase {
  name: string;
  term_id: string;
  location_id: string;
  level: string;
  prerequisites: string | null;
}
export interface Session extends RecordBase {
  class_id: string;
  starts_at: string;
  ends_at: string;
  capacity: number;
  students: string[];
}
export interface Conversation extends RecordBase {
  student_id: string;
  subject: string | null;
}
export interface Message extends RecordBase {
  conversation_id: string;
  kind: string;
  body: string;
  occurred_at: string;
}
export type RunStatus =
  | "running"
  | "awaiting_review"
  | "finalizing"
  | "approved"
  | "closed"
  | "superseded"
  | "failed";
export interface EnquiryAnswer {
  question: string;
  status: "answered" | "needs_student" | "needs_teacher";
  answer: string;
  references: string[];
}
export interface Run extends RecordBase {
  conversation_id: string;
  source_message_id: string;
  draft_message_id: string | null;
  approved_response_id: string | null;
  status: RunStatus;
  revision: number;
  interpretation: Record<string, unknown>;
  evidence: Record<string, unknown>[];
  draft_details: {
    body?: string;
    rationale?: string;
    questions?: string[];
    references?: string[];
    booking_session_id?: string | null;
    answers?: EnquiryAnswer[];
  };
  policy_snapshot: Record<string, unknown>;
  error: string | null;
}
export interface RunSummary extends RecordBase {
  student_id: string;
  student_name: string;
  student_email: string;
  conversation_id: string;
  source_message_id: string;
  status: RunStatus;
  revision: number;
  request_summary: string;
  routing?: Record<string, unknown> | null;
  flow?: string | null;
  error: string | null;
}
export interface Examples {
  version: number;
  as_of: string;
  notice: string;
  students: Student[];
  terms: Term[];
  locations: Location[];
  classes: StudioClass[];
  class_sessions: Session[];
  enrolments: Enrolment[];
  conversations: Conversation[];
  messages: Message[];
  agent_runs: Run[];
}
export interface Identity {
  authenticated: boolean;
  login_available?: boolean;
  csrf_token?: string;
  user?: { email: string; name: string };
}
