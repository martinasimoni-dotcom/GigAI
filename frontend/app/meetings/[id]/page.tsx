'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { GigAIClient } from '@/lib/api';

interface MeetingDetail {
  meeting_id: string;
  title: string;
  date: string;
  project: string;
  participants: string[];
  duration_minutes: number;
  summary: string;
}

interface Decision {
  order: number;
  space: string;
  element: string;
  action: string;
  description: string;
  assigned_to: string;
  priority: string;
  deadline: string;
}

interface Revision {
  revision_id: string;
  space_name: string;
  element_type: string;
  comment_text: string;
  applied_at: string;
}

export default function MeetingDetailPage() {
  const params = useParams();
  const meetingId = params.id as string;

  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [transcript, setTranscript] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'transcript' | 'decisions' | 'revisions'>('overview');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const api = new GigAIClient('http://localhost:8000');

        // Fetch in parallel
        const [meetingData, transcriptData, decisionsData, revisionsData] = await Promise.all([
          api.getMeetingDetail?.(meetingId),
          api.getMeetingTranscript?.(meetingId),
          api.getMeetingDecisions?.(meetingId),
          api.getMeetingRevisions?.(meetingId),
        ]).catch((err) => {
          throw new Error(err.message);
        });

        if (meetingData) setMeeting(meetingData);
        if (transcriptData) setTranscript(transcriptData);
        if (decisionsData) setDecisions(decisionsData);
        if (revisionsData) setRevisions(revisionsData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load meeting details');
      } finally {
        setLoading(false);
      }
    };

    if (meetingId) {
      fetchData();
    }
  }, [meetingId]);

  const getPriorityColor = (priority: string) => {
    switch (priority.toUpperCase()) {
      case 'HIGH':
        return { bg: '#fee2e2', text: '#991b1b' };
      case 'MEDIUM':
        return { bg: '#fef3c7', text: '#92400e' };
      case 'LOW':
        return { bg: '#dbeafe', text: '#1e40af' };
      default:
        return { bg: '#f3f4f6', text: '#374151' };
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
        Loading meeting details...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '2rem' }}>
        <Link href="/meetings">Back to Meetings</Link>
        <div
          style={{
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '1rem',
            borderRadius: '0.5rem',
            marginTop: '1rem',
          }}
        >
          Error: {error}
        </div>
      </div>
    );
  }

  if (!meeting) {
    return (
      <div style={{ padding: '2rem' }}>
        <Link href="/meetings">Back to Meetings</Link>
        <p style={{ marginTop: '1rem', color: '#6b7280' }}>Meeting not found</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem' }}>
      <Link href="/meetings" style={{ color: '#3b82f6', textDecoration: 'none' }}>
        Back to Meetings
      </Link>

      <div style={{ marginTop: '1.5rem', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          {meeting.title}
        </h1>
        <p style={{ color: '#6b7280', marginBottom: '1rem' }}>
          {new Date(meeting.date).toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <span style={{ color: '#6b7280', fontSize: '0.875rem' }}>Project</span>
            <p style={{ fontWeight: '600', marginTop: '0.25rem' }}>{meeting.project}</p>
          </div>
          <div>
            <span style={{ color: '#6b7280', fontSize: '0.875rem' }}>Participants</span>
            <p style={{ fontWeight: '600', marginTop: '0.25rem' }}>{meeting.participants.length} people</p>
          </div>
          <div>
            <span style={{ color: '#6b7280', fontSize: '0.875rem' }}>Duration</span>
            <p style={{ fontWeight: '600', marginTop: '0.25rem' }}>{meeting.duration_minutes} minutes</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid #e5e7eb', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '0' }}>
          {(['overview', 'transcript', 'decisions', 'revisions'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: '1rem',
                borderBottom: activeTab === tab ? '2px solid #3b82f6' : 'none',
                color: activeTab === tab ? '#3b82f6' : '#6b7280',
                backgroundColor: 'transparent',
                border: 'none',
                cursor: 'pointer',
                fontWeight: activeTab === tab ? '600' : '400',
                textTransform: 'capitalize',
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div>
          <div style={{ marginBottom: '2rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>
              Meeting Summary
            </h2>
            <p style={{ lineHeight: '1.6', color: '#374151' }}>
              {meeting.summary || 'No summary available'}
            </p>
          </div>

          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>
              Participants
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
              {meeting.participants.map((participant) => (
                <div
                  key={participant}
                  style={{
                    backgroundColor: '#f9fafb',
                    padding: '1rem',
                    borderRadius: '0.5rem',
                    border: '1px solid #e5e7eb',
                  }}
                >
                  {participant}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'transcript' && (
        <div>
          <div
            style={{
              backgroundColor: '#f9fafb',
              padding: '1.5rem',
              borderRadius: '0.5rem',
              border: '1px solid #e5e7eb',
              maxHeight: '600px',
              overflowY: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              lineHeight: '1.6',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {transcript || 'Transcript not available'}
          </div>
        </div>
      )}

      {activeTab === 'decisions' && (
        <div>
          {decisions.length === 0 ? (
            <p style={{ color: '#6b7280' }}>No decisions recorded for this meeting</p>
          ) : (
            <div style={{ display: 'grid', gap: '1rem' }}>
              {decisions.map((decision) => {
                const priorityColor = getPriorityColor(decision.priority);
                return (
                  <div
                    key={decision.order}
                    style={{
                      border: '1px solid #e5e7eb',
                      borderRadius: '0.5rem',
                      padding: '1.5rem',
                      backgroundColor: '#fff',
                    }}
                  >
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '1rem', marginBottom: '1rem' }}>
                      <div>
                        <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.25rem' }}>
                          {decision.space} - {decision.action}
                        </h3>
                        <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
                          Element: {decision.element}
                        </p>
                      </div>
                      <div>
                        <span
                          style={{
                            backgroundColor: priorityColor.bg,
                            color: priorityColor.text,
                            padding: '0.5rem 0.75rem',
                            borderRadius: '0.25rem',
                            fontSize: '0.875rem',
                            fontWeight: '600',
                          }}
                        >
                          {decision.priority}
                        </span>
                      </div>
                    </div>
                    <p style={{ marginBottom: '1rem', color: '#374151' }}>
                      {decision.description}
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', fontSize: '0.875rem' }}>
                      <div>
                        <span style={{ color: '#6b7280' }}>Assigned To</span>
                        <p style={{ fontWeight: '600', marginTop: '0.25rem' }}>
                          {decision.assigned_to}
                        </p>
                      </div>
                      <div>
                        <span style={{ color: '#6b7280' }}>Deadline</span>
                        <p style={{ fontWeight: '600', marginTop: '0.25rem' }}>
                          {new Date(decision.deadline).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === 'revisions' && (
        <div>
          {revisions.length === 0 ? (
            <p style={{ color: '#6b7280' }}>No revisions applied yet</p>
          ) : (
            <div style={{ display: 'grid', gap: '1rem' }}>
              {revisions.map((revision) => (
                <div
                  key={revision.revision_id}
                  style={{
                    border: '2px solid #fca5a5',
                    borderRadius: '0.5rem',
                    padding: '1.5rem',
                    backgroundColor: '#fef2f2',
                  }}
                >
                  <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '1rem', marginBottom: '1rem', alignItems: 'start' }}>
                    <div
                      style={{
                        width: '32px',
                        height: '32px',
                        backgroundColor: '#dc2626',
                        borderRadius: '0.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        fontWeight: 'bold',
                        fontSize: '1.25rem',
                      }}
                    >
                      R
                    </div>
                    <div>
                      <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.25rem' }}>
                        {revision.space_name}
                      </h3>
                      <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
                        Element: {revision.element_type}
                      </p>
                    </div>
                  </div>
                  <div style={{ backgroundColor: '#fff', padding: '1rem', borderRadius: '0.375rem', marginBottom: '1rem', fontSize: '0.875rem' }}>
                    {revision.comment_text}
                  </div>
                  <p style={{ color: '#6b7280', fontSize: '0.75rem' }}>
                    Applied: {new Date(revision.applied_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
