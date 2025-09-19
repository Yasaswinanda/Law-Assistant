import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Layout } from '../components/Layout';

export const AuthPage: React.FC = () => {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'client' | 'lawyer'>('client');
  const [locationName, setLocationName] = useState('');
  const [location, setLocation] = useState<{ lat?: number; lon?: number }>({});
  const [geoInfo, setGeoInfo] = useState('No location yet');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { login, register } = useAuth();

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mode') === 'signup') {
      setIsSignup(true);
    }
  }, []);

  const handleUseGeo = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setLocation({ lat: latitude, lon: longitude });
          setGeoInfo(`Location: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`);
        },
        (error) => {
          setGeoInfo('Location access denied');
        }
      );
    } else {
      setGeoInfo('Geolocation not supported');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (isSignup) {
        await register(email, password, role, {
          name: locationName || undefined,
          lat: location.lat,
          lon: location.lon,
        });
      } else {
        await login(email, password);
      }
      window.location.href = '/dashboard';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout currentPage="auth">
      <div className="card" style={{ maxWidth: '680px', margin: '0 auto' }}>
        <div className="tabs">
          <button
            className={`btn ${!isSignup ? 'active' : ''}`}
            onClick={() => setIsSignup(false)}
          >
            Sign In
          </button>
          <button
            className={`btn ${isSignup ? 'active' : ''}`}
            onClick={() => setIsSignup(true)}
          >
            Create Account
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {!isSignup ? (
            <div className="grid" style={{ gridTemplateColumns: '1fr', gap: '12px' }}>
              <div className="field">
                <label>Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </div>
              <div className="field">
                <label>Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
              </div>
              <div className="row">
                <button type="submit" className="btn prime" disabled={isLoading}>
                  {isLoading ? 'Signing In...' : 'Sign In'}
                </button>
              </div>
            </div>
          ) : (
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="field" style={{ gridColumn: '1 / -1' }}>
                <label>Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </div>
              <div className="field">
                <label>Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Choose a strong password"
                  autoComplete="new-password"
                  required
                />
              </div>
              <div className="field">
                <label>Role</label>
                <select value={role} onChange={(e) => setRole(e.target.value as 'client' | 'lawyer')}>
                  <option value="client">Client</option>
                  <option value="lawyer">Lawyer</option>
                </select>
              </div>
              <div className="field" style={{ gridColumn: '1 / -1' }}>
                <label>Location name (optional)</label>
                <input
                  type="text"
                  value={locationName}
                  onChange={(e) => setLocationName(e.target.value)}
                  placeholder="e.g., Bangalore, Koramangala"
                />
              </div>
              <div className="row">
                <button type="button" className="btn" onClick={handleUseGeo}>
                  Use my location
                </button>
                <span className="pill muted">{geoInfo}</span>
              </div>
              <div className="row" style={{ gridColumn: '1 / -1' }}>
                <button type="submit" className="btn prime" disabled={isLoading}>
                  {isLoading ? 'Creating Account...' : 'Create Account'}
                </button>
              </div>
            </div>
          )}
        </form>

        {error && (
          <div className="toast" style={{ display: 'block', position: 'relative', margin: '16px 0 0 0' }}>
            {error}
          </div>
        )}
      </div>
    </Layout>
  );
};