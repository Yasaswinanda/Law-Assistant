import React from 'react';
import { Navigation } from './Navigation';

interface LayoutProps {
  children: React.ReactNode;
  currentPage?: string;
}

export const Layout: React.FC<LayoutProps> = ({ children, currentPage }) => {
  return (
    <>
      <Navigation currentPage={currentPage} />
      <main className="shell">
        {children}
      </main>
    </>
  );
};