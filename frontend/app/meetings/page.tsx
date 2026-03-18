'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { GigAIClient } from '@/lib/api';

interface Meeting {
  meeting_id: string;
  title: string;
  date: string;
  project: string;
  participants_count: number;
  duration_minutes: number;
  changes_count: number;
  decisions_count: number;
}

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'today' | 'week'>('all');

  useEffect(() => {
    const fetchMeetings = async () => {
      try {
        setLoading(true);
        const api = new GigAIClient('http://localhost:8000');
        const data = await api.getMeetings();
        setMeetings(data || []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load meetings');
      } finally {
        setLoading(false);
      }
    };

    fetchMeetings();
  }, []);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredMeetings = meetings.filter((meeting) => {
    if (filter === 'all') return true;
    const meetingDate = new Date(meeting.date);
    const today = new Date();
    const daysDiff = (today.getTime() - meetingDate.getTime()) / (1000 * 60 * 60 * 24);
    if (filter === 'today') return daysDiff <= 1;
    if (filter === 'week') return daysDiff <= 7;
    return true;
  });

  return (
    <div style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          Meetings
        </h1>
        <p style={{ color: '#6b7280' }}>
          Manage and track architectural coordination meetings
        </p>
      </div>

      {/* Filter Tabs */}
      <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem', borderBottom: '1px solid #e5e7eb' }}>
        {(['all', 'today', 'week'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '0.75rem 1rem',
              borderBottom: filter === f ? '2px solid #3b82f6' : 'none',
              color: filter === f ? '#3b82f6' : '#6b7280',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: filter === f ? '600' : '400',
            }}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
          Loading meetings...
        </div>
      ) : error ? (
        <div
          style={{
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '1rem',
            borderRadius: '0.5rem',
            marginBottom: '1rem',
          }}
        >
          Error: {error}
        </div>
      ) : filteredMeetings.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
          No meetings found.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {filteredMeetings.map((meeting) => (
            <Link
              key={meeting.meeting_id}
              href={`/meetings/${meeting.meeting_id}`}
              style={{ textDecoration: 'none' }}
            >
              <div
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '0.5rem',
                  padding: '1.5rem',
                  backgroundColor: '#fff',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  hover: {
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  },
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'start', gap: '1rem' }}>
                  <div>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                      {meeting.title}
                    </h3>
                    <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                      {formatDate(meeting.date)}
                    </p>
                    <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                      <div>
                        <span style={{ color: '#6b7280', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          Project
                        </span>
                        <p style={{ fontWeight: '600', margin: '0.25rem 0 0 0' }}>
                          {meeting.project}
                        </p>
                      </div>
                      <div>
                        <span style={{ color: '#6b7280', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          Participants
                        </span>
                        <p style={{ fontWeight: '600', margin: '0.25rem 0 0 0' }}>
                          {meeting.participants_count}
                        </p>
                      </div>
                      <div>
                        <span style={{ color: '#6b7280', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                          Duration
                        </span>
                        <p style={{ fontWeight: '600', margin: '0.25rem 0 0 0' }}>
                          {meeting.duration_minutes} min
                        </p>
                      </div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ marginBottom: '0.5rem' }}>
                      <span
                        style={{
                          backgroundColor: '#dbeafe',
                          color: '#1e40af',
                          padding: '0.25rem 0.75rem',
                          borderRadius: '0.25rem',
                          fontSize: '0.875rem',
                          fontWeight: '600',
                        }}
                      >
                        {meeting.changes_count} Changes
                      </span>
                    </div>
                    <div>
                      <span
                        style={{
                          backgroundColor: '#dcfce7',
                          color: '#15803d',
                          padding: '0.25rem 0.75rem',
                          borderRadius: '0.25rem',
                          fontSize: '0.875rem',
                          fontWeight: '600',
                        }}
                      >
                        {meeting.decisions_count} Decisions
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
