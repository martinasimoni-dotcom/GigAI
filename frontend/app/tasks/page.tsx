/*
Task Board - Kanban View
Drag-and-drop task management interface
*/

'use client';

import React, { useState, useEffect } from 'react';
import { resolveApiBaseUrl } from '@/lib/api';

export default function TaskBoard() {
  const [tasks, setTasks] = useState({ pending: [], in_progress: [], completed: [] });
  const [loading, setLoading] = useState(true);
  const [draggedTask, setDraggedTask] = useState(null);

  useEffect(() => {
    const apiUrl = resolveApiBaseUrl();

    // Fetch tasks and organize by status
    fetch(`${apiUrl}/api/tasks`)
      .then((res) => res.json())
      .then((allTasks) => {
        const organized = {
          pending: allTasks.filter((t) => t.status === 'pending'),
          in_progress: allTasks.filter((t) => t.status === 'in_progress'),
          completed: allTasks.filter((t) => t.status === 'completed'),
        };
        setTasks(organized);
        setLoading(false);
      })
      .catch((error) => {
        console.error('Error fetching tasks:', error);
        setLoading(false);
      });
  }, []);

  const handleDragStart = (task) => {
    setDraggedTask(task);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = async (newStatus) => {
    if (!draggedTask) return;

    const apiUrl = resolveApiBaseUrl();

    // Update task status on backend
    await fetch(`${apiUrl}/api/tasks/${draggedTask.task_id}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_status: newStatus }),
    });

    // Update local state
    const oldStatus = draggedTask.status;
    setTasks((prev) => ({
      ...prev,
      [oldStatus]: prev[oldStatus].filter((t) => t.task_id !== draggedTask.task_id),
      [newStatus]: [
        ...prev[newStatus],
        { ...draggedTask, status: newStatus },
      ],
    }));

    setDraggedTask(null);
  };

  if (loading) {
    return <div className="text-gray-600 p-8">Loading tasks...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Task Board</h1>
        <p className="text-gray-600 mt-2">
          Drag tasks between columns to update status
        </p>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KanbanColumn
          title="Pending"
          status="pending"
          tasks={tasks.pending}
          color="bg-yellow-50"
          borderColor="border-yellow-200"
          onDragOver={handleDragOver}
          onDrop={() => handleDrop('pending')}
        >
          {tasks.pending.map((task) => (
            <TaskCard
              key={task.task_id}
              task={task}
              onDragStart={() => handleDragStart(task)}
            />
          ))}
        </KanbanColumn>

        <KanbanColumn
          title="In Progress"
          status="in_progress"
          tasks={tasks.in_progress}
          color="bg-blue-50"
          borderColor="border-blue-200"
          onDragOver={handleDragOver}
          onDrop={() => handleDrop('in_progress')}
        >
          {tasks.in_progress.map((task) => (
            <TaskCard
              key={task.task_id}
              task={task}
              onDragStart={() => handleDragStart(task)}
            />
          ))}
        </KanbanColumn>

        <KanbanColumn
          title="Completed"
          status="completed"
          tasks={tasks.completed}
          color="bg-green-50"
          borderColor="border-green-200"
          onDragOver={handleDragOver}
          onDrop={() => handleDrop('completed')}
        >
          {tasks.completed.map((task) => (
            <TaskCard
              key={task.task_id}
              task={task}
              onDragStart={() => handleDragStart(task)}
            />
          ))}
        </KanbanColumn>
      </div>

      {/* Summary */}
      <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Summary</h2>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-3xl font-bold text-yellow-600">
              {tasks.pending.length}
            </p>
            <p className="text-gray-600 text-sm mt-2">Pending</p>
          </div>
          <div>
            <p className="text-3xl font-bold text-blue-600">
              {tasks.in_progress.length}
            </p>
            <p className="text-gray-600 text-sm mt-2">In Progress</p>
          </div>
          <div>
            <p className="text-3xl font-bold text-green-600">
              {tasks.completed.length}
            </p>
            <p className="text-gray-600 text-sm mt-2">Completed</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Component: Kanban Column
function KanbanColumn({
  title,
  status,
  tasks,
  color,
  borderColor,
  onDragOver,
  onDrop,
  children,
}) {
  return (
    <div
      className={`rounded-lg ${color} border-2 ${borderColor} p-4 min-h-96`}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-gray-900">{title}</h2>
        <span className="bg-gray-200 text-gray-800 text-xs font-semibold px-3 py-1 rounded-full">
          {tasks.length}
        </span>
      </div>

      <div className="space-y-3">{children}</div>
    </div>
  );
}

// Component: Task Card
function TaskCard({ task, onDragStart }) {
  const priorityColor = {
    HIGH: 'bg-red-100 text-red-800',
    MEDIUM: 'bg-yellow-100 text-yellow-800',
    LOW: 'bg-green-100 text-green-800',
  }[task.priority];

  const daysUntilDue = task.days_until_due;
  const isOverdue = daysUntilDue < 0;

  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="bg-white rounded-lg p-4 shadow-sm hover:shadow-md transition cursor-grab active:cursor-grabbing border border-gray-200"
    >
      {/* Task Title */}
      <h3 className="font-semibold text-gray-900 text-sm mb-2">
        {task.action}: {task.space}
      </h3>

      {/* Assigned To */}
      <p className="text-gray-600 text-xs mb-3">
        👤 {task.assigned_to_name}
      </p>

      {/* Tags */}
      <div className="flex justify-between items-center mb-3">
        <span className={`text-xs font-semibold px-2 py-1 rounded ${priorityColor}`}>
          {task.priority}
        </span>
        <span
          className={`text-xs font-semibold px-2 py-1 rounded ${
            isOverdue
              ? 'bg-red-100 text-red-800'
              : daysUntilDue <= 3
              ? 'bg-orange-100 text-orange-800'
              : 'bg-blue-100 text-blue-800'
          }`}
        >
          {isOverdue
            ? `${Math.abs(daysUntilDue)}d overdue`
            : `${daysUntilDue}d left`}
        </span>
      </div>

      {/* Deadline */}
      <p className="text-gray-600 text-xs">
        📅 Due: {task.deadline}
      </p>
    </div>
  );
}
