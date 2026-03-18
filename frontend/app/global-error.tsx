'use client';

import React from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html>
      <body>
        <div className="flex items-center justify-center min-h-screen bg-gray-50">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Application Error
            </h1>
            <p className="text-gray-600 mb-4">
              {error.message || 'An unexpected error occurred!'}
            </p>
            <button
              onClick={() => reset()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Try again
            </button>
          </div>
          <style jsx>{`
            body {
              margin: 0;
              padding: 0;
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                'Helvetica Neue', Arial, sans-serif;
            }
            .flex {
              display: flex;
            }
            .items-center {
              align-items: center;
            }
            .justify-center {
              justify-content: center;
            }
            .min-h-screen {
              min-height: 100vh;
            }
            .bg-gray-50 {
              background-color: #f9fafb;
            }
            .text-center {
              text-align: center;
            }
            .text-4xl {
              font-size: 2.25rem;
            }
            .text-gray-900 {
              color: #111827;
            }
            .text-gray-600 {
              color: #4b5563;
            }
            .font-bold {
              font-weight: 700;
            }
            .mb-2 {
              margin-bottom: 0.5rem;
            }
            .mb-4 {
              margin-bottom: 1rem;
            }
            .px-4 {
              padding-left: 1rem;
              padding-right: 1rem;
            }
            .py-2 {
              padding-top: 0.5rem;
              padding-bottom: 0.5rem;
            }
            .bg-blue-600 {
              background-color: #2563eb;
            }
            .text-white {
              color: white;
            }
            .rounded-lg {
              border-radius: 0.5rem;
            }
            .hover\:bg-blue-700:hover {
              background-color: #1d4ed8;
            }
            .transition {
              transition-property: all;
              transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
              transition-duration: 150ms;
            }
          `}</style>
        </div>
      </body>
    </html>
  );
}
