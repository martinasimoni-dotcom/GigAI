'use client';

import { useState } from 'react';

interface Setting {
  id: string;
  label: string;
  description: string;
  value: string | boolean;
  type: 'text' | 'toggle' | 'select';
  options?: { label: string; value: string }[];
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Setting[]>([
    {
      id: 'email_notifications',
      label: 'Email Notifications',
      description: 'Receive email when new tasks are assigned',
      value: true,
      type: 'toggle',
    },
    {
      id: 'daily_digest',
      label: 'Daily Digest',
      description: 'Get a summary email of all activity',
      value: true,
      type: 'toggle',
    },
    {
      id: 'desktop_notifications',
      label: 'Desktop Notifications',
      description: 'Show desktop alerts for urgent updates',
      value: true,
      type: 'toggle',
    },
    {
      id: 'notification_time',
      label: 'Digest Time',
      description: 'Time to receive daily digest',
      value: '09:00',
      type: 'text',
    },
    {
      id: 'theme',
      label: 'Theme',
      description: 'Choose your preferred theme',
      value: 'light',
      type: 'select',
      options: [
        { label: 'Light', value: 'light' },
        { label: 'Dark', value: 'dark' },
        { label: 'Auto', value: 'auto' },
      ],
    },
    {
      id: 'items_per_page',
      label: 'Items Per Page',
      description: 'Number of items to show in lists',
      value: '20',
      type: 'select',
      options: [
        { label: '10', value: '10' },
        { label: '20', value: '20' },
        { label: '50', value: '50' },
      ],
    },
  ]);

  const [saved, setSaved] = useState(false);

  const handleToggle = (id: string) => {
    setSettings(
      settings.map((s) =>
        s.id === id ? { ...s, value: !s.value } : s
      )
    );
    setSaved(false);
  };

  const handleChange = (id: string, value: string) => {
    setSettings(
      settings.map((s) =>
        s.id === id ? { ...s, value } : s
      )
    );
    setSaved(false);
  };

  const handleSave = async () => {
    try {
      // In production: POST to /api/settings
      await new Promise((resolve) => setTimeout(resolve, 500));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Failed to save settings', error);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '800px' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          Settings
        </h1>
        <p style={{ color: '#6b7280' }}>
          Manage your dashboard preferences and notification settings
        </p>
      </div>

      {/* Success Message */}
      {saved && (
        <div
          style={{
            backgroundColor: '#dcfce7',
            color: '#15803d',
            padding: '1rem',
            borderRadius: '0.5rem',
            marginBottom: '2rem',
            border: '1px solid #86efac',
          }}
        >
          Settings saved successfully!
        </div>
      )}

      {/* Settings Sections */}
      <div style={{ display: 'grid', gap: '2rem' }}>
        {/* Notifications Section */}
        <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>
            Notifications
          </h2>

          {settings
            .filter((s) => ['email_notifications', 'daily_digest', 'desktop_notifications', 'notification_time'].includes(s.id))
            .map((setting) => (
              <div key={setting.id} style={{ marginBottom: '1.5rem' }}>
                {setting.type === 'toggle' ? (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '1rem', alignItems: 'start' }}>
                    <div>
                      <label style={{ display: 'block', fontWeight: '600', marginBottom: '0.25rem' }}>
                        {setting.label}
                      </label>
                      <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
                        {setting.description}
                      </p>
                    </div>
                    <button
                      onClick={() => handleToggle(setting.id)}
                      style={{
                        width: '56px',
                        height: '32px',
                        backgroundColor: (setting.value as boolean) ? '#3b82f6' : '#d1d5db',
                        border: 'none',
                        borderRadius: '9999px',
                        cursor: 'pointer',
                        transition: 'background-color 0.2s',
                        position: 'relative',
                      }}
                    >
                      <div
                        style={{
                          width: '28px',
                          height: '28px',
                          backgroundColor: '#fff',
                          borderRadius: '9999px',
                          position: 'absolute',
                          top: '2px',
                          left: (setting.value as boolean) ? '26px' : '2px',
                          transition: 'left 0.2s',
                        }}
                      />
                    </button>
                  </div>
                ) : (
                  <div>
                    <label style={{ display: 'block', fontWeight: '600', marginBottom: '0.5rem' }}>
                      {setting.label}
                    </label>
                    <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                      {setting.description}
                    </p>
                    <input
                      type="time"
                      value={setting.value as string}
                      onChange={(e) => handleChange(setting.id, e.target.value)}
                      style={{
                        width: '100%',
                        maxWidth: '200px',
                        padding: '0.5rem',
                        border: '1px solid #d1d5db',
                        borderRadius: '0.375rem',
                      }}
                    />
                  </div>
                )}
              </div>
            ))}
        </div>

        {/* Display Section */}
        <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>
            Display
          </h2>

          {settings
            .filter((s) => ['theme', 'items_per_page'].includes(s.id))
            .map((setting) => (
              <div key={setting.id} style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', fontWeight: '600', marginBottom: '0.5rem' }}>
                  {setting.label}
                </label>
                <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                  {setting.description}
                </p>
                <select
                  value={setting.value as string}
                  onChange={(e) => handleChange(setting.id, e.target.value)}
                  style={{
                    width: '100%',
                    maxWidth: '300px',
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    backgroundColor: '#fff',
                    cursor: 'pointer',
                  }}
                >
                  {setting.options?.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            ))}
        </div>

        {/* API Settings */}
        <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>
            API Configuration
          </h2>
          <p style={{ color: '#6b7280', marginBottom: '1rem' }}>
            Current API endpoint: http://localhost:8000
          </p>
          <div style={{ backgroundColor: '#f9fafb', padding: '1rem', borderRadius: '0.375rem', fontFamily: 'monospace', fontSize: '0.875rem' }}>
            <p>Dashboard API: /api/dashboard/*</p>
            <p>Meetings API: /api/meetings/*</p>
            <p>Tasks API: /api/tasks/*</p>
            <p>Revisions API: /api/revisions/*</p>
            <p>WebSocket: /ws/dashboard/*</p>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div style={{ marginTop: '2rem', paddingTop: '2rem', borderTop: '1px solid #e5e7eb' }}>
        <button
          onClick={handleSave}
          style={{
            backgroundColor: '#3b82f6',
            color: '#fff',
            padding: '0.75rem 2rem',
            border: 'none',
            borderRadius: '0.5rem',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '1rem',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#2563eb';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#3b82f6';
          }}
        >
          Save Settings
        </button>
      </div>
    </div>
  );
}
