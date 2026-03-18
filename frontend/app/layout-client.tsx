'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function LayoutClient({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  const navItems = [
    { name: 'Dashboard', href: '/', icon: '📊' },
    { name: 'Meetings', href: '/meetings', icon: '📅' },
    { name: 'Tasks', href: '/tasks', icon: '📋' },
    { name: 'Revisions', href: '/revisions', icon: '🔴' },
    { name: 'Team', href: '/team', icon: '👥' },
    { name: 'Settings', href: '/settings', icon: '⚙️' },
  ];

  const isActive = (href: string) => {
    return pathname === href || (href !== '/' && pathname.startsWith(href));
  };

  return (
    <div className="flex min-h-screen">
      {/* Sidebar Navigation */}
      <aside className="hidden md:flex flex-col w-64 bg-white border-r border-gray-200 shadow-sm">
        {/* Logo */}
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-blue-600">GigAI</h1>
          <p className="text-xs text-gray-600 mt-1">
            Meeting Intelligence
          </p>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-4 py-6 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.href}
              href={item.href}
              isActive={isActive(item.href)}
              icon={item.icon}
              name={item.name}
            />
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 text-center">
          <p className="text-xs text-gray-600">v0.3.0</p>
          <p className="text-xs text-gray-500 mt-1">Phase 3 Dashboard</p>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 bg-white border-b border-gray-200 z-50">
        <div className="flex items-center justify-between p-4">
          <h1 className="text-xl font-bold text-blue-600">GigAI</h1>
          <MobileMenuButton />
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 mt-16 md:mt-0 pb-8">
        {children}
      </main>

      <style jsx global>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        html {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
            'Helvetica Neue', Arial, sans-serif;
        }

        body {
          color: #111827;
          background-color: #f9fafb;
        }
      `}</style>
      <style jsx>{`
        .flex {
          display: flex;
        }
        .flex-col {
          flex-direction: column;
        }
        .items-center {
          align-items: center;
        }
        .justify-between {
          justify-content: space-between;
        }
        .gap-3 {
          gap: 0.75rem;
        }
        .min-h-screen {
          min-height: 100vh;
        }
        .p-2 {
          padding: 0.5rem;
        }
        .p-4 {
          padding: 1rem;
        }
        .p-6 {
          padding: 1.5rem;
        }
        .px-4 {
          padding-left: 1rem;
          padding-right: 1rem;
        }
        .py-3 {
          padding-top: 0.75rem;
          padding-bottom: 0.75rem;
        }
        .py-6 {
          padding-top: 1.5rem;
          padding-bottom: 1.5rem;
        }
        .mt-1 {
          margin-top: 0.25rem;
        }
        .mt-16 {
          margin-top: 4rem;
        }
        .mb-4 {
          margin-bottom: 1rem;
        }
        .pb-8 {
          padding-bottom: 2rem;
        }
        .flex-1 {
          flex: 1;
        }
        .w-64 {
          width: 16rem;
        }
        .bg-white {
          background-color: white;
        }
        .bg-gray-50 {
          background-color: #f9fafb;
        }
        .bg-blue-50 {
          background-color: #eff6ff;
        }
        .text-gray-600 {
          color: #4b5563;
        }
        .text-gray-700 {
          color: #374151;
        }
        .text-gray-500 {
          color: #6b7280;
        }
        .text-blue-600 {
          color: #2563eb;
        }
        .text-xs {
          font-size: 0.75rem;
        }
        .text-sm {
          font-size: 0.875rem;
        }
        .text-lg {
          font-size: 1.125rem;
        }
        .text-xl {
          font-size: 1.25rem;
        }
        .text-2xl {
          font-size: 1.5rem;
        }
        .font-bold {
          font-weight: 700;
        }
        .font-semibold {
          font-weight: 600;
        }
        .border-b {
          border-bottom: 1px solid #e5e7eb;
        }
        .border-r {
          border-right: 1px solid #e5e7eb;
        }
        .rounded-lg {
          border-radius: 0.5rem;
        }
        .shadow-sm {
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        .transition {
          transition-property: all;
          transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
          transition-duration: 150ms;
        }
        .hover\:bg-gray-50:hover {
          background-color: #f9fafb;
        }
        .hover\:bg-gray-100:hover {
          background-color: #f3f4f6;
        }
        .z-50 {
          z-index: 50;
        }
        .space-y-2 > * + * {
          margin-top: 0.5rem;
        }
        .fixed {
          position: fixed;
        }
        .top-0 {
          top: 0;
        }
        .left-0 {
          left: 0;
        }
        .right-0 {
          right: 0;
        }

        @media (max-width: 768px) {
          .hidden {
            display: none;
          }
          .md\\:hidden {
            display: block;
          }
          .md\\:flex {
            display: none;
          }
          .md\\:mt-0 {
            margin-top: 0;
          }
        }

        @media (min-width: 768px) {
          .md\\:hidden {
            display: none;
          }
          .md\\:flex {
            display: flex;
          }
          .md\\:mt-0 {
            margin-top: 0;
          }
        }
      `}</style>
    </div>
  );
}

function NavLink({
  href,
  isActive,
  icon,
  name,
}: {
  href: string;
  isActive: boolean;
  icon: string;
  name: string;
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${
        isActive
          ? 'bg-blue-50 text-blue-600 font-semibold'
          : 'text-gray-700 hover:bg-gray-50'
      }`}
    >
      <span className="text-xl">{icon}</span>
      <span>{name}</span>
    </Link>
  );
}

function MobileMenuButton() {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <button
      onClick={() => setIsOpen(!isOpen)}
      className="p-2 rounded-lg hover:bg-gray-100"
    >
      <svg
        className="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 6h16M4 12h16M4 18h16"
        />
      </svg>
    </button>
  );
}
