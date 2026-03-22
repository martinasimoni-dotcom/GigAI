/*
GigAI API Client
Frontend utility for API communication
*/

const DEFAULT_API_PORT = '8010';

function trimTrailingSlash(value: string) {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

function getConfiguredApiBase() {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  return configured ? trimTrailingSlash(configured) : null;
}

export function resolveApiBaseUrl() {
  const configured = getConfiguredApiBase();
  if (configured) {
    return configured;
  }

  if (typeof window !== 'undefined') {
    // Use the Next.js same-origin rewrite in browser by default to avoid
    // localhost vs 127.0.0.1 CORS mismatches during local development.
    return '';
  }

  return `http://localhost:${DEFAULT_API_PORT}`;
}

function resolveWebSocketBaseUrl(httpBaseUrl: string) {
  if (httpBaseUrl) {
    return new URL(httpBaseUrl);
  }

  if (typeof window !== 'undefined') {
    return new URL(`${window.location.protocol}//${window.location.hostname}:${DEFAULT_API_PORT}`);
  }

  return new URL(`http://localhost:${DEFAULT_API_PORT}`);
}

export interface DashboardSocketMessage {
  type: string;
  timestamp: string;
  revision?: {
    revision_id: string;
    meeting_id: string;
    meeting_title: string;
    project_id: string;
    space_name: string;
    element_type: string;
    action: string;
    comment_text: string;
    remarks: string;
    applied_at: string;
    applied_by: string;
    priority: string;
    status: string;
    view_name: string;
    view_type: string;
    cloud_id: string;
    note_id: string;
    source_event_id?: number | null;
  };
  data?: {
    pending_tasks?: number;
    overdue_tasks?: number;
    completed_today?: number;
    total_revisions?: number;
  };
}

export class GigAIClient {
  baseUrl: string;

  constructor(baseUrl: string = resolveApiBaseUrl()) {
    this.baseUrl = trimTrailingSlash(baseUrl);
  }

  async get(endpoint: string) {
    const response = await fetch(`${this.baseUrl}${endpoint}`);
    if (!response.ok) throw new Error(`API Error: ${response.status}`);
    return response.json();
  }

  async post(endpoint: string, data: any) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`API Error: ${response.status}`);
    return response.json();
  }

  // Meetings
  async getMeetings(limit = 10, skip = 0) {
    return this.get(`/api/meetings?limit=${limit}&skip=${skip}`);
  }

  async getMeetingDetail(meetingId: string) {
    return this.get(`/api/meetings/${meetingId}`);
  }

  async getMeetingTranscript(meetingId: string) {
    const response = await this.get(`/api/meetings/${meetingId}/transcript`);
    return response?.transcript || response?.transcript_text || '';
  }

  async getMeetingDecisions(meetingId: string) {
    const response = await this.get(`/api/meetings/${meetingId}/decisions`);
    return response?.decisions || [];
  }

  // Tasks
  async getTasks(filters: any = {}) {
    const params = new URLSearchParams(filters).toString();
    return this.get(`/api/tasks${params ? '?' + params : ''}`);
  }

  async getTask(taskId: string) {
    return this.get(`/api/tasks/${taskId}`);
  }

  async updateTaskStatus(taskId: string, newStatus: string) {
    return this.post(`/api/tasks/${taskId}/status`, { new_status: newStatus });
  }

  // Dashboard
  async getDashboardSummary() {
    return this.get('/api/dashboard/summary');
  }

  async getDashboardTimeline() {
    return this.get('/api/dashboard/timeline');
  }

  async getTeamWorkload() {
    const response = await this.get('/api/dashboard/architects');
    return {
      members: response?.architects || [],
      stats: response?.stats || null,
    };
  }

  // Revisions
  async getRevisions() {
    const response = await this.get('/api/revisions');
    return response?.revisions || [];
  }

  async getMeetingRevisions(meetingId: string) {
    const response = await this.get(`/api/meetings/${meetingId}/revisions`);
    return response?.revisions || [];
  }

  // Export
  async exportMeetingPDF(meetingId: string) {
    return this.get(`/api/export/meeting/${meetingId}/pdf`);
  }

  // WebSocket
  connectWebSocket(sessionId: string) {
    const apiUrl = resolveWebSocketBaseUrl(this.baseUrl);
    const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${apiUrl.host}/ws/dashboard/${sessionId}`;
    return new WebSocket(wsUrl);
  }
}

export const apiClient = new GigAIClient();
