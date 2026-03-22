'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { DashboardSocketMessage, GigAIClient, apiClient } from '@/lib/api';

interface RevisionItem {
  revision_id: string;
  meeting_id: string;
  meeting_title: string;
  project_id?: string;
  space_name: string;
  element_type: string;
  action: string;
  comment_text: string;
  remarks?: string;
  applied_at: string;
  applied_by: string;
  priority: string;
  status?: string;
  view_name?: string;
  view_type?: string;
  cloud_id?: string;
  note_id?: string;
}

export default function RevisionsPage() {
  const [revisions, setRevisions] = useState<RevisionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [liveSyncMessage, setLiveSyncMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'this-week' | 'this-month'>('all');
  const [sortBy, setSortBy] = useState<'recent' | 'space' | 'priority'>('recent');

  useEffect(() => {
    const mergeRevision = (incoming: RevisionItem) => {
      setRevisions((current) => {
        const existing = current.find((item) => item.revision_id === incoming.revision_id);
        if (existing) {
          return current.map((item) =>
            item.revision_id === incoming.revision_id ? { ...item, ...incoming } : item
          );
        }
        return [incoming, ...current];
      });
    };

    const fetchRevisions = async () => {
      try {
        setLoading(true);
        const api = new GigAIClient();
        const data = await api.getRevisions();
        setRevisions(data || []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load revisions');
      } finally {
        setLoading(false);
      }
    };

    const socket = apiClient.connectWebSocket('revisions-page');
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as DashboardSocketMessage;
      if (payload.type === 'revision_marked' && payload.revision) {
        setLiveSyncMessage(`Live sync active. Last update for ${payload.revision.space_name}.`);
        mergeRevision(payload.revision);
      }
    };

    socket.onerror = () => {
      setLiveSyncMessage('Live sync is unavailable. Showing latest fetched revisions.');
    };

    fetchRevisions();

    return () => {
      socket.close();
    };
  }, []);

  const filteredRevisions = revisions.filter((revision) => {
    if (filter === 'all') return true;
    const revDate = new Date(revision.applied_at);
    const today = new Date();
    const daysDiff = (today.getTime() - revDate.getTime()) / (1000 * 60 * 60 * 24);
    if (filter === 'this-week') return daysDiff <= 7;
    if (filter === 'this-month') return daysDiff <= 30;
    return true;
  });

  const sortedRevisions = [...filteredRevisions].sort((a, b) => {
    if (sortBy === 'recent') {
      return new Date(b.applied_at).getTime() - new Date(a.applied_at).getTime();
    } else if (sortBy === 'space') {
      return a.space_name.localeCompare(b.space_name);
    } else if (sortBy === 'priority') {
      const priorityMap = { HIGH: 0, MEDIUM: 1, LOW: 2 };
      return (priorityMap[a.priority as keyof typeof priorityMap] || 3) - (priorityMap[b.priority as keyof typeof priorityMap] || 3);
    }
    return 0;
  });

  const getPriorityColor = (priority: string) => {
    switch (priority.toUpperCase()) {
      case 'HIGH':
        return { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' };
      case 'MEDIUM':
        return { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' };
      case 'LOW':
        return { bg: '#dbeafe', text: '#1e40af', border: '#93c5fd' };
      default:
        return { bg: '#f3f4f6', text: '#374151', border: '#e5e7eb' };
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          Revision Tracking
        </h1>
        <p style={{ color: '#6b7280' }}>
          Monitor all Revit revision clouds applied to the model
        </p>
      </div>

      {/* Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
            Filter by Date
          </label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              backgroundColor: '#fff',
              cursor: 'pointer',
            }}
          >
            <option value="all">All Revisions</option>
            <option value="this-week">This Week</option>
            <option value="this-month">This Month</option>
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
            Sort By
          </label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              backgroundColor: '#fff',
              cursor: 'pointer',
            }}
          >
            <option value="recent">Most Recent</option>
            <option value="space">Space Name</option>
            <option value="priority">Priority</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      {!loading && (
        <div style={{ display: 'grid', gap: '1rem', marginBottom: '2rem' }}>
          {liveSyncMessage ? (
            <div style={{ backgroundColor: '#eff6ff', color: '#1d4ed8', padding: '0.875rem 1rem', borderRadius: '0.5rem', border: '1px solid #bfdbfe' }}>
              {liveSyncMessage}
            </div>
          ) : null}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
            <div style={{ backgroundColor: '#f3f4f6', padding: '1rem', borderRadius: '0.5rem' }}>
            <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Total Revisions</p>
            <p style={{ fontSize: '1.875rem', fontWeight: 'bold', marginTop: '0.25rem' }}>
              {sortedRevisions.length}
            </p>
          </div>
          <div style={{ backgroundColor: '#fee2e2', padding: '1rem', borderRadius: '0.5rem' }}>
            <p style={{ color: '#991b1b', fontSize: '0.875rem', fontWeight: '600' }}>High Priority</p>
            <p style={{ fontSize: '1.875rem', fontWeight: 'bold', marginTop: '0.25rem', color: '#991b1b' }}>
              {sortedRevisions.filter((r) => r.priority === 'HIGH').length}
            </p>
          </div>
          <div style={{ backgroundColor: '#fef3c7', padding: '1rem', borderRadius: '0.5rem' }}>
            <p style={{ color: '#92400e', fontSize: '0.875rem', fontWeight: '600' }}>Medium Priority</p>
            <p style={{ fontSize: '1.875rem', fontWeight: 'bold', marginTop: '0.25rem', color: '#92400e' }}>
              {sortedRevisions.filter((r) => r.priority === 'MEDIUM').length}
            </p>
          </div>
          </div>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
          Loading revisions...
        </div>
      ) : error ? (
        <div
          style={{
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '1rem',
            borderRadius: '0.5rem',
          }}
        >
          Error: {error}
        </div>
      ) : sortedRevisions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
          No revisions found.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {sortedRevisions.map((revision) => {
            const colors = getPriorityColor(revision.priority);
            return (
              <Link
                key={revision.revision_id}
                href={`/meetings/${revision.meeting_id}`}
                style={{ textDecoration: 'none' }}
              >
                <div
                  style={{
                    border: `2px solid ${colors.border}`,
                    borderRadius: '0.5rem',
                    padding: '1.5rem',
                    backgroundColor: colors.bg,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: '1rem', alignItems: 'start' }}>
                    {/* Icon */}
                    <div
                      style={{
                        width: '40px',
                        height: '40px',
                        backgroundColor: colors.text,
                        borderRadius: '0.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        fontWeight: 'bold',
                        fontSize: '1.5rem',
                      }}
                    >
                      R
                    </div>

                    {/* Content */}
                    <div>
                      <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: colors.text, marginBottom: '0.25rem' }}>
                        {revision.space_name}
                      </h3>
                      <p style={{ color: colors.text, opacity: 0.7, fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                        {revision.action} • {revision.element_type}
                      </p>
                      <p style={{ color: colors.text, fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                        {revision.comment_text}
                      </p>
                      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.75rem' }}>
                        <span style={{ color: colors.text, opacity: 0.7 }}>
                          Meeting: {revision.meeting_title}
                        </span>
                        <span style={{ color: colors.text, opacity: 0.7 }}>
                          Applied by: {revision.applied_by}
                        </span>
                        <span style={{ color: colors.text, opacity: 0.7 }}>
                          {new Date(revision.applied_at).toLocaleString()}
                        </span>
                        {revision.view_name ? (
                          <span style={{ color: colors.text, opacity: 0.7 }}>
                            View: {revision.view_name}
                          </span>
                        ) : null}
                      </div>
                      {revision.cloud_id || revision.note_id ? (
                        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                          {revision.cloud_id ? (
                            <span style={{ color: colors.text, opacity: 0.7 }}>
                              Cloud: {revision.cloud_id}
                            </span>
                          ) : null}
                          {revision.note_id ? (
                            <span style={{ color: colors.text, opacity: 0.7 }}>
                              Note: {revision.note_id}
                            </span>
                          ) : null}
                        </div>
                      ) : null}
                    </div>

                    {/* Priority Badge */}
                    <div>
                      <span
                        style={{
                          backgroundColor: 'rgba(255, 255, 255, 0.5)',
                          color: colors.text,
                          padding: '0.5rem 0.75rem',
                          borderRadius: '0.25rem',
                          fontSize: '0.875rem',
                          fontWeight: '600',
                          display: 'inline-block',
                        }}
                      >
                        {revision.priority}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
