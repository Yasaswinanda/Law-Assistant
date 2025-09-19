import React from 'react';
import { useAuth } from '../contexts/AuthContext';

interface NavigationProps {
  currentPage?: string;
}

export const Navigation: React.FC<NavigationProps> = ({ currentPage }) => {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    window.location.href = '/';
  };

  return (
    <header className="nav">
      <div className="row">
        <div className="brand">
          <span className="dot"></span> Legal Assistant
        </div>
        <div className="row">
          {user ? (
            <>
              {currentPage !== 'dashboard' && (
                <a className="btn" href="/dashboard">Dashboard</a>
              )}
              {currentPage !== 'chat' && (
                <a className="btn" href="/chat">AI Assistant</a>
              )}
              {currentPage !== 'profile' && (
                <a className="btn" href="/profile">Profile</a>
              )}
              <button className="btn" onClick={handleLogout}>Logout</button>
            </>
          ) : (
            <>
              {currentPage !== 'home' && (
                <a className="btn" href="/">Home</a>
              )}
              {currentPage !== 'auth' && (
                <>
                  <a className="btn" href="/auth">Sign In</a>
                  <a className="btn prime" href="/auth?mode=signup">Create Account</a>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </header>
  );
};