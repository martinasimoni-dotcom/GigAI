'use client';

import { useState, useEffect } from 'react';
import { GigAIClient } from '@/lib/api';

interface TeamMember {
  name: string;
  role: string;
  email: string;
  pending_tasks: number;
  in_progress_tasks: number;
  completed_tasks: number;
  workload_percentage: number;
  overdue_count: number;
  upcoming_deadline: string | null;
}

interface TeamStats {
  total_members: number;
  total_tasks: number;
  avg_workload: number;
  overdue_count: number;
  completion_rate: number;
}

export default function TeamPage() {
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [stats, setStats] = useState<TeamStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'workload' | 'pending' | 'name'>('workload');

  useEffect(() => {
    const fetchTeamData = async () => {
      try {
        setLoading(true);
        const api = new GigAIClient('http://localhost:8000');
        const data = await api.getTeamWorkload?.();

        if (data) {
          setTeam(data.members || []);
          setStats(data.stats || null);
        }
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load team data');
      } finally {
        setLoading(false);
      }
    };

    fetchTeamData();
  }, []);

  const sortedTeam = [...team].sort((a, b) => {
    if (sortBy === 'workload') {
      return b.workload_percentage - a.workload_percentage;
    } else if (sortBy === 'pending') {
      return b.pending_tasks - a.pending_tasks;
    } else if (sortBy === 'name') {
      return a.name.localeCompare(b.name);
    }
    return 0;
  });

  const getWorkloadColor = (percentage: number) => {
    if (percentage >= 80) return { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' };
    if (percentage >= 50) return { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' };
    return { bg: '#dcfce7', text: '#15803d', border: '#86efac' };
  };

  return (
    <div style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          Team Workload
        </h1>
        <p style={{ color: '#6b7280' }}>
          Monitor team capacity and task assignments
        </p>
      </div>

      {/* Overall Stats */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          <div style={{ backgroundColor: '#f3f4f6', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb' }}>
            <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Team Members</p>
            <p style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>{stats.total_members}</p>
          </div>
          <div style={{ backgroundColor: '#dbeafe', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #93c5fd' }}>
            <p style={{ color: '#1e40af', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Active Tasks</p>
            <p style={{ fontSize: '2.25rem', fontWeight: 'bold', color: '#1e40af' }}>{stats.total_tasks}</p>
          </div>
          <div style={{ backgroundColor: '#dcfce7', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #86efac' }}>
            <p style={{ color: '#15803d', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Completion Rate</p>
            <p style={{ fontSize: '2.25rem', fontWeight: 'bold', color: '#15803d' }}>
              {stats.completion_rate}%
            </p>
          </div>
          <div style={{ backgroundColor: '#fee2e2', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #fca5a5' }}>
            <p style={{ color: '#991b1b', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Overdue Tasks</p>
            <p style={{ fontSize: '2.25rem', fontWeight: 'bold', color: '#991b1b' }}>{stats.overdue_count}</p>
          </div>
        </div>
      )}

      {/* Filter */}
      <div style={{ marginBottom: '2rem' }}>
        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
          Sort By
        </label>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as any)}
          style={{
            padding: '0.5rem',
            border: '1px solid #d1d5db',
            borderRadius: '0.375rem',
            backgroundColor: '#fff',
            cursor: 'pointer',
            maxWidth: '300px',
          }}
        >
          <option value="workload">Highest Workload</option>
          <option value="pending">Most Pending Tasks</option>
          <option value="name">Alphabetical</option>
        </select>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
          Loading team data...
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
      ) : sortedTeam.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
          No team members found.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          {sortedTeam.map((member) => {
            const workloadColor = getWorkloadColor(member.workload_percentage);
            const totalTasks = member.pending_tasks + member.in_progress_tasks + member.completed_tasks;

            return (
              <div
                key={member.email}
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '0.5rem',
                  padding: '1.5rem',
                  backgroundColor: '#fff',
                }}
              >
                {/* Header */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '1rem', marginBottom: '1rem', alignItems: 'start' }}>
                  <div>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.25rem' }}>
                      {member.name}
                    </h3>
                    <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                      {member.role}
                    </p>
                    <p style={{ color: '#3b82f6', fontSize: '0.875rem' }}>
                      {member.email}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>Workload</p>
                    <div
                      style={{
                        fontSize: '1.875rem',
                        fontWeight: 'bold',
                        color: workloadColor.text,
                      }}
                    >
                      {member.workload_percentage}%
                    </div>
                  </div>
                </div>

                {/* Workload Bar */}
                <div style={{ marginBottom: '1rem' }}>
                  <div
                    style={{
                      width: '100%',
                      height: '12px',
                      backgroundColor: '#e5e7eb',
                      borderRadius: '9999px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${member.workload_percentage}%`,
                        height: '100%',
                        backgroundColor: workloadColor.text,
                        transition: 'width 0.3s',
                      }}
                    />
                  </div>
                </div>

                {/* Stats */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div style={{ backgroundColor: '#fef3c7', padding: '0.75rem', borderRadius: '0.375rem' }}>
                    <p style={{ color: '#92400e', fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                      Pending
                    </p>
                    <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#92400e' }}>
                      {member.pending_tasks}
                    </p>
                  </div>
                  <div style={{ backgroundColor: '#dbeafe', padding: '0.75rem', borderRadius: '0.375rem' }}>
                    <p style={{ color: '#1e40af', fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                      In Progress
                    </p>
                    <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1e40af' }}>
                      {member.in_progress_tasks}
                    </p>
                  </div>
                  <div style={{ backgroundColor: '#dcfce7', padding: '0.75rem', borderRadius: '0.375rem' }}>
                    <p style={{ color: '#15803d', fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                      Completed
                    </p>
                    <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#15803d' }}>
                      {member.completed_tasks}
                    </p>
                  </div>
                </div>

                {/* Alerts */}
                {member.overdue_count > 0 && (
                  <div
                    style={{
                      backgroundColor: '#fee2e2',
                      color: '#991b1b',
                      padding: '0.75rem',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      marginBottom: '0.5rem',
                    }}
                  >
                    {member.overdue_count} overdue task{member.overdue_count !== 1 ? 's' : ''}
                  </div>
                )}

                {member.upcoming_deadline && (
                  <div
                    style={{
                      backgroundColor: '#f3f4f6',
                      padding: '0.75rem',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem',
                      color: '#374151',
                    }}
                  >
                    Next deadline: {new Date(member.upcoming_deadline).toLocaleDateString()}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
