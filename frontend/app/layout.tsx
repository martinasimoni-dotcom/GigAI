/*
GigAI Dashboard Layout
Main layout for all pages with navigation
*/

import React from 'react';
import LayoutClient from './layout-client';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>GigAI Meeting Intelligence Dashboard</title>
        <meta
          name="description"
          content="Real-time coordination dashboard for architectural meeting intelligence"
        />
      </head>
      <body>
        <LayoutClient>{children}</LayoutClient>
      </body>
    </html>
  );
}
