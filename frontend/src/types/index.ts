export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  is_active: boolean;
  timezone: string;
}

export interface AdoCredential {
  id: number;
  provider: 'client' | 'mycompany' | 'rysun';
  org_url: string;
  is_valid: boolean;
  has_pat: boolean;
  resolved_identity_id?: string;
  resolved_identity_name?: string;
  resolved_identity_email?: string;
  last_verified_at?: string;
  last_error?: string;
}

export interface ActivityItem {
  id: number;
  source_type: 'commit' | 'pull_request' | 'review' | 'work_item' | 'branch';
  external_id: string;
  repository?: string;
  project?: string;
  branch?: string;
  author_id?: string;
  author_name?: string;
  author_email?: string;
  occurred_at: string;
  date_str: string;
  title: string;
  description?: string;
  url?: string;
  related_ids?: string;
  is_excluded: boolean;
}

export interface ManualActivity {
  id: number;
  date_str: string;
  category: string;
  description: string;
  duration_hours: number;
  project_name?: string;
  notes?: string;
}

export interface SummaryVersion {
  id: number;
  version_number: number;
  source: string;
  summary_text: string;
  created_at: string;
}

export interface TimesheetEntry {
  id: number;
  date_str: string;
  day_of_week: string;
  client_name: string;
  project_name: string;
  area_path: string;
  iteration_path: string;
  hours: number;
  ph: boolean;
  leave: boolean;
  half_day: boolean;
  wfh: boolean;
  task_summary: string;
  detailed_bullets: string[];
  is_user_approved: boolean;
  submission_status: 'draft' | 'pending_review' | 'submitted' | 'failed';
  mycompany_workitem_id?: number;
  ry_workitem_id?: number;
  last_error?: string;
  existing_mycompany_item?: any;
  existing_rysun_item?: any;
}

export interface WeeklyReview {
  week_start: string;
  week_end: string;
  total_hours: number;
  approved_count: number;
  submitted_count: number;
  entries: TimesheetEntry[];
}
