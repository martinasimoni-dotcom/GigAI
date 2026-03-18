/*
GigAI API Client
Frontend utility for API communication
*/

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class GigAIClient {
  baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
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
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' ? window.location.host : 'localhost:3000';
    const wsUrl = `${protocol}//${host}/ws/dashboard/${sessionId}`;
    return new WebSocket(wsUrl);
  }
}

export const apiClient = new GigAIClient();
