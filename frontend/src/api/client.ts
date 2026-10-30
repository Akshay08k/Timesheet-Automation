import type { User, AdoCredential, ActivityItem, ManualActivity, WeeklyReview, TimesheetEntry, SummaryVersion } from '../types';

const API_BASE = '/api';

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.dispatchEvent(new Event('auth-expired'));
    throw new Error('Session expired. Please log in again.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Auth
  async login(formData: FormData) {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    return response.json();
  },

  async register(data: any): Promise<User> {
    return request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getMe(): Promise<User> {
    return request<User>('/auth/me');
  },

  // Credentials
  async getCredentials(): Promise<AdoCredential[]> {
    return request<AdoCredential[]>('/credentials');
  },

  async saveCredential(data: { provider: 'client' | 'rysun'; org_url: string; pat: string }): Promise<AdoCredential> {
    return request<AdoCredential>('/credentials', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteCredential(provider: 'client' | 'rysun'): Promise<void> {
    return request<void>(`/credentials/${provider}`, {
      method: 'DELETE',
    });
  },

  // Activities
  async getActivities(dateStr?: string, sourceType?: string): Promise<ActivityItem[]> {
    const params = new URLSearchParams();
    if (dateStr) params.append('date_str', dateStr);
    if (sourceType) params.append('source_type', sourceType);
    return request<ActivityItem[]>(`/activities?${params.toString()}`);
  },

  async syncActivities(startDate: string, endDate: string): Promise<any> {
    return request('/activities/sync', {
      method: 'POST',
      body: JSON.stringify({ start_date: startDate, end_date: endDate }),
    });
  },

  async toggleExcludeActivity(activityId: number): Promise<ActivityItem> {
    return request<ActivityItem>(`/activities/${activityId}/toggle-exclude`, {
      method: 'PATCH',
    });
  },

  // Manual Activities
  async getManualActivities(dateStr?: string): Promise<ManualActivity[]> {
    const params = dateStr ? `?date_str=${dateStr}` : '';
    return request<ManualActivity[]>(`/manual-activities${params}`);
  },

  async createManualActivity(data: Partial<ManualActivity>): Promise<ManualActivity> {
    return request<ManualActivity>('/manual-activities', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteManualActivity(id: number): Promise<void> {
    return request<void>(`/manual-activities/${id}`, {
      method: 'DELETE',
    });
  },

  // AI Summaries (Gemini API)
  async generateDailySummary(dateStr: string, customInstruction?: string): Promise<any> {
    return request('/summaries/generate', {
      method: 'POST',
      body: JSON.stringify({
        date_str: dateStr,
        custom_instruction: customInstruction,
      }),
    });
  },

  async getSummaryVersions(dateStr: string): Promise<SummaryVersion[]> {
    return request<SummaryVersion[]>(`/summaries/${dateStr}/versions`);
  },

  // Timesheets
  async getWeeklyReview(mondayDateStr: string): Promise<WeeklyReview> {
    return request<WeeklyReview>(`/timesheets/week/${mondayDateStr}`);
  },

  async updateTimesheetDraft(draftId: number, data: Partial<TimesheetEntry>): Promise<TimesheetEntry> {
    return request<TimesheetEntry>(`/timesheets/drafts/${draftId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async submitSingleDay(draftId: number, forceUpdate = false): Promise<any> {
    return request('/timesheets/submit-day', {
      method: 'POST',
      body: JSON.stringify({
        draft_id: draftId,
        force_update_existing: forceUpdate,
      }),
    });
  },

  async submitWeek(draftIds: number[], forceUpdate = false): Promise<any[]> {
    return request('/timesheets/submit-week', {
      method: 'POST',
      body: JSON.stringify({
        draft_ids: draftIds,
        force_update_existing: forceUpdate,
      }),
    });
  },
};
