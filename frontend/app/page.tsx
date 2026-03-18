'use client';

import React, { useState, useEffect } from 'react';
import StatCard from '@/components/StatCard';
import Card from '@/components/Card';
import PieChart from '@/components/charts/PieChart';

export default function DashboardHome() {
  const [summary, setSummary] = useState({
    total_meetings: 2,
    total_changes: 4,
    total_tasks: 4,
    pending_tasks: 3,
    overdue_tasks: 0,
    completed_tasks: 1,
    high_priority_tasks: 1,
  });

  const [metrics, setMetrics] = useState({
    trends: {
      meetings_trend: 12,
      changes_trend: 25,
      completion_trend: -5,
    },
    priority_distribution: {
      HIGH: 8,
      MEDIUM: 15,
      LOW: 21,
    },
    status_distribution: {
      pending: 10,
      in_progress: 12,
      completed: 22,
    },
  });

  const [timelineData, setTimelineData] = useState([
    { date: '03/09', pending: 12, in_progress: 5, completed: 8, completion_rate: 45 },
    { date: '03/10', pending: 11, in_progress: 6, completed: 9, completion_rate: 50 },
    { date: '03/11', pending: 10, in_progress: 7, completed: 10, completion_rate: 55 },
    { date: '03/12', pending: 9, in_progress: 6, completed: 12, completion_rate: 60 },
    { date: '03/13', pending: 8, in_progress: 8, completed: 13, completion_rate: 63 },
    { date: '03/14', pending: 7, in_progress: 7, completed: 14, completion_rate: 65 },
    { date: '03/15', pending: 3, in_progress: 4, completed: 8, completion_rate: 68 },
  ]);

  const [meetings, setMeetings] = useState([
    {
      meeting_id: 'meet_001',
      title: 'Architecture Coordination - Phase 5',
      date: new Date().toISOString(),
      project: 'Residential Tower A',
      participants_count: 4,
      changes_detected: 4,
      tasks_assigned: 4,
      status: 'completed',
    },
  ]);

  const [architects, setArchitects] = useState([
    {
      name: 'Alice Johnson',
      role: 'Unit Designer',
      workload_percentage: 75,
      pending_tasks: 3,
      in_progress_tasks: 2,
      completed_tasks: 8,
    },
    {
      name: 'David Lee',
      role: 'M&E Lead',
      workload_percentage: 50,
      pending_tasks: 2,
      in_progress_tasks: 1,
      completed_tasks: 5,
    },
  ]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    Promise.all([
      fetch(`${apiUrl}/api/dashboard/summary`).then((res) => res.json()).catch(() => summary),
      fetch(`${apiUrl}/api/dashboard/metrics`).then((res) => res.json()).catch(() => metrics),
      fetch(`${apiUrl}/api/dashboard/timeline?days=7`).then((res) => res.json()).catch(() => ({ timeline: timelineData })),
      fetch(`${apiUrl}/api/meetings?limit=3`).then((res) => res.json()).catch(() => meetings),
      fetch(`${apiUrl}/api/dashboard/architects`).then((res) => res.json()).catch(() => ({ architects })),
    ])
      .then(([summaryData, metricsData, timelineDataResponse, meetingsData, architectsData]) => {
        if (summaryData.total_meetings !== undefined) setSummary(summaryData);
        if (metricsData.trends) setMetrics(metricsData);
        if (timelineDataResponse.timeline) setTimelineData(timelineDataResponse.timeline);
        if (Array.isArray(meetingsData)) setMeetings(meetingsData);
        if (architectsData.architects) setArchitects(architectsData.architects);
      })
      .catch((err) => console.log('Using mock data:', err));
  }, []);

  const statusChartData = [
    { name: 'Pending', value: summary.pending_tasks, color: '#FFA500' },
    { name: 'In Progress', value: Math.max(1, summary.total_tasks - summary.pending_tasks - summary.completed_tasks), color: '#45B7D1' },
    { name: 'Completed', value: summary.completed_tasks, color: '#4ECDC4' },
  ];

  const priorityChartData = [
    { name: 'HIGH', value: summary.high_priority_tasks, color: '#FF6B6B' },
    { name: 'MEDIUM', value: Math.max(0, summary.total_tasks - summary.high_priority_tasks - 2), color: '#FFA500' },
    { name: 'LOW', value: 2, color: '#4ECDC4' },
  ];

  const completionRate = summary.total_tasks ? Math.round((summary.completed_tasks / summary.total_tasks) * 100) : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-gray-100 p-4 md:p-8">
      {/* Header */}
      <div className="mb-12 animate-fadeIn">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-3">
          📊 GigAI Dashboard
        </h1>
        <p className="text-lg text-gray-600">Real-time architectural design coordination & task management</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
        <StatCard title="Total Meetings" value={summary.total_meetings} icon="📅" color="blue" trend={{ direction: 'up', value: metrics.trends.meetings_trend }} />
        <StatCard title="Design Changes" value={summary.total_changes} icon="🎨" color="purple" trend={{ direction: 'up', value: metrics.trends.changes_trend }} />
        <StatCard title="Active Tasks" value={summary.total_tasks} icon="📋" color="orange" />
        <StatCard title="Completion Rate" value={`${completionRate}%`} icon="✅" color="green" trend={{ direction: 'up', value: 15 }} />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
        {/* Task Status Distribution Chart */}
        <Card title="📈 Task Status Distribution" subtitle="Breakdown of task statuses" padding="lg">
          <div className="w-full h-80 flex items-center justify-center">
            <PieChart data={statusChartData} height={320} innerRadius={60} />
          </div>
        </Card>

        {/* Priority Distribution Chart */}
        <Card title="🎯 Priority Distribution (Main View)" subtitle="Tasks by priority level - Focus on HIGH priority!" padding="lg">
          <div className="w-full h-80 flex items-center justify-center bg-gradient-to-br from-red-50 to-orange-50 rounded-lg">
            <PieChart data={priorityChartData} height={320} innerRadius={60} />
          </div>
        </Card>
      </div>

      {/* Completion Trend Chart */}
      <Card title="📉 Completion Trend (Last 7 Days)" subtitle="Task completion rate over time" padding="lg" className="mb-12">
        <div className="w-full">
          <div className="h-80 w-full">
            <svg viewBox="0 0 1000 400" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
              {/* Grid lines */}
              <line x1="80" y1="50" x2="80" y2="350" stroke="#ccc" strokeWidth="2" />
              <line x1="80" y1="350" x2="950" y2="350" stroke="#ccc" strokeWidth="2" />

              {/* Grid background */}
              <defs>
                <linearGradient id="trendGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#4ECDC4" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#4ECDC4" stopOpacity="0.01" />
                </linearGradient>
              </defs>

              {/* Y-axis labels */}
              {[0, 20, 40, 60, 80, 100].map((val, i) => (
                <g key={i}>
                  <text x="60" y={350 - (val / 100) * 280 + 5} fontSize="12" fill="#999" textAnchor="end">
                    {val}%
                  </text>
                  <line x1="75" y1={350 - (val / 100) * 280} x2="950" y2={350 - (val / 100) * 280} stroke="#eee" strokeWidth="1" strokeDasharray="4,4" />
                </g>
              ))}

              {/* Area under line */}
              <path
                d={`M 100 ${350 - (timelineData[0]?.completion_rate || 0) / 100 * 280} ${timelineData
                  .map((d, i) => `L ${100 + (i / (timelineData.length - 1 || 1)) * 850} ${350 - (d.completion_rate / 100) * 280}`)
                  .join(' ')} L ${950} 350 L 100 350 Z`}
                fill="url(#trendGradient)"
              />

              {/* Line chart */}
              <polyline
                points={timelineData
                  .map((d, i) => `${100 + (i / (timelineData.length - 1 || 1)) * 850},${350 - (d.completion_rate / 100) * 280}`)
                  .join(' ')}
                stroke="#4ECDC4"
                strokeWidth="3"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Data points */}
              {timelineData.map((d, i) => (
                <g key={i}>
                  <circle cx={100 + (i / (timelineData.length - 1 || 1)) * 850} cy={350 - (d.completion_rate / 100) * 280} r="6" fill="white" stroke="#4ECDC4" strokeWidth="2" />
                  <text x={100 + (i / (timelineData.length - 1 || 1)) * 850} y="375" fontSize="12" fill="#666" textAnchor="middle">
                    {d.date}
                  </text>
                  <text x={100 + (i / (timelineData.length - 1 || 1)) * 850} y={320 - (d.completion_rate / 100) * 280} fontSize="11" fill="#4ECDC4" fontWeight="bold" textAnchor="middle">
                    {d.completion_rate}%
                  </text>
                </g>
              ))}
            </svg>
          </div>
        </div>
      </Card>

      {/* Task Workload Over Time */}
      <Card title="📊 Task Workload Trend" subtitle="Pending, In Progress, and Completed tasks over time" padding="lg" className="mb-12">
        <div className="w-full h-80">
          <svg viewBox="0 0 1000 400" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
            {/* Y-axis */}
            <line x1="80" y1="50" x2="80" y2="350" stroke="#999" strokeWidth="2" />
            {/* X-axis */}
            <line x1="80" y1="350" x2="950" y2="350" stroke="#999" strokeWidth="2" />

            {/* Bars */}
            {timelineData.map((d, i) => {
              const barWidth = 90;
              const spacing = 120;
              const startX = 100 + i * spacing;
              const scale = 350 / 20;

              return (
                <g key={i}>
                  {/* Pending (Orange) */}
                  <rect x={startX} y={350 - d.pending * scale} width={barWidth / 3 - 2} height={d.pending * scale} fill="#FFA500" opacity="0.8" />
                  {/* In Progress (Blue) */}
                  <rect x={startX + barWidth / 3} y={350 - d.in_progress * scale} width={barWidth / 3 - 2} height={d.in_progress * scale} fill="#45B7D1" opacity="0.8" />
                  {/* Completed (Teal) */}
                  <rect x={startX + (barWidth * 2) / 3} y={350 - d.completed * scale} width={barWidth / 3 - 2} height={d.completed * scale} fill="#4ECDC4" opacity="0.8" />
                  {/* Date label */}
                  <text x={startX + barWidth / 2} y="375" fontSize="12" fill="#666" textAnchor="middle">
                    {d.date}
                  </text>
                </g>
              );
            })}

            {/* Legend */}
            <rect x="100" y="20" width="15" height="15" fill="#FFA500" />
            <text x="125" y="32" fontSize="12" fill="#666">
              Pending
            </text>

            <rect x="300" y="20" width="15" height="15" fill="#45B7D1" />
            <text x="325" y="32" fontSize="12" fill="#666">
              In Progress
            </text>

            <rect x="520" y="20" width="15" height="15" fill="#4ECDC4" />
            <text x="545" y="32" fontSize="12" fill="#666">
              Completed
            </text>
          </svg>
        </div>
      </Card>

      {/* Recent Meetings & Team Workload */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
        <div className="lg:col-span-2">
          <Card title="📅 Recent Meetings" subtitle="Latest team activities">
            <div className="space-y-4">
              {meetings.map((meeting) => (
                <div key={meeting.meeting_id} className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-transparent rounded-lg hover:shadow-lg transition-all border border-blue-100">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{meeting.title}</h3>
                    <p className="text-gray-600 text-sm mt-1">
                      {meeting.project} · 👥 {meeting.participants_count} participants
                    </p>
                    <p className="text-gray-500 text-xs mt-1">{new Date(meeting.date).toLocaleString()}</p>
                  </div>
                  <div className="text-right">
                    <div className="flex gap-6 text-sm">
                      <div className="text-center">
                        <p className="font-bold text-orange-600 text-lg">{meeting.changes_detected}</p>
                        <p className="text-gray-600 text-xs">changes</p>
                      </div>
                      <div className="text-center">
                        <p className="font-bold text-blue-600 text-lg">{meeting.tasks_assigned}</p>
                        <p className="text-gray-600 text-xs">tasks</p>
                      </div>
                    </div>
                    <span className="mt-3 inline-block px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">{meeting.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card title="👥 Team Workload" subtitle="Architect availability">
          <div className="space-y-6">
            {architects.map((arch) => (
              <div key={arch.name} className="space-y-2">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-gray-900">{arch.name}</p>
                    <p className="text-gray-600 text-xs">{arch.role}</p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${arch.workload_percentage >= 80 ? 'bg-red-100 text-red-800' : arch.workload_percentage >= 50 ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
                    {arch.workload_percentage}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-3 rounded-full transition-all duration-500 ${
                      arch.workload_percentage >= 80
                        ? 'bg-gradient-to-r from-red-400 to-red-600'
                        : arch.workload_percentage >= 50
                        ? 'bg-gradient-to-r from-yellow-400 to-orange-500'
                        : 'bg-gradient-to-r from-green-400 to-green-600'
                    }`}
                    style={{ width: `${arch.workload_percentage}%` }}
                  ></div>
                </div>
                <p className="text-gray-600 text-xs">📋 {arch.pending_tasks}✈️ {arch.in_progress_tasks} 🔄 ✅ {arch.completed_tasks}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Quick Stats Footer */}
      <Card title="⚡ Quick Stats" subtitle="Summary metrics">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gradient-to-br from-green-50 to-transparent rounded-lg">
            <p className="text-3xl font-bold text-green-600">{completionRate}%</p>
            <p className="text-gray-600 text-sm mt-2">Completion Rate</p>
          </div>
          <div className="text-center p-4 bg-gradient-to-br from-red-50 to-transparent rounded-lg">
            <p className="text-3xl font-bold text-red-600">{summary.high_priority_tasks}</p>
            <p className="text-gray-600 text-sm mt-2">HIGH Priority</p>
          </div>
          <div className="text-center p-4 bg-gradient-to-br from-blue-50 to-transparent rounded-lg">
            <p className="text-3xl font-bold text-blue-600">{summary.total_meetings}</p>
            <p className="text-gray-600 text-sm mt-2">Total Meetings</p>
          </div>
          <div className="text-center p-4 bg-gradient-to-br from-purple-50 to-transparent rounded-lg">
            <p className="text-3xl font-bold text-purple-600">{architects.length}</p>
            <p className="text-gray-600 text-sm mt-2">Team Members</p>
          </div>
        </div>
      </Card>

      <style jsx global>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fadeIn {
          animation: fadeIn 0.5s ease-out;
        }
      `}</style>
    </div>
  );
}
