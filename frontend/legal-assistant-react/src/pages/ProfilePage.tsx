import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Layout } from '../components/Layout';

export const ProfilePage: React.FC = () => {
  const { user, token } = useAuth();
  const [locationName, setLocationName] = useState(user?.location_name || '');
  const [location, setLocation] = useState<{ lat?: number; lon?: number }>({
    lat: user?.location_lat,
    lon: user?.location_lon,
  });
  const [geoInfo, setGeoInfo] = useState(
    user?.location_lat && user?.location_lon
      ? `Location: ${user.location_lat.toFixed(4)}, ${user.location_lon.toFixed(4)}`
      : 'No location set'
  );
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';

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
    setIsLoading(true);
    setMessage('');

    try {
      const response = await fetch(`${API_BASE}/me/location`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          location_name: locationName || null,
          location_lat: location.lat || null,
          location_lon: location.lon || null,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessage('Profile updated successfully!');
        
        // Update the auth context with new user data
        window.location.reload(); // Simple approach to refresh user data
      } else {
        const error = await response.json();
        setMessage(`Error: ${error.error}`);
      }
    } catch (error) {
      setMessage('Error: Failed to update profile');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout currentPage="profile">
      <div className="row">
        <div className="card" style={{ flex: '1 1 400px' }}>
          <h2 style={{ margin: '0 0 6px 0' }}>Profile Settings</h2>
          <div className="divider"></div>

          <form onSubmit={handleSubmit}>
            <div className="grid" style={{ gap: '16px' }}>
              <div className="kv">
                <div className="muted">Email:</div>
                <div>{user?.email}</div>
              </div>

              <div className="kv">
                <div className="muted">Role:</div>
                <div style={{ textTransform: 'capitalize' }}>{user?.role}</div>
              </div>

              <div className="kv">
                <div className="muted">Member since:</div>
                <div>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown'}</div>
              </div>

              <div className="divider"></div>

              <div className="field">
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

              <div className="row">
                <button type="submit" className="btn prime" disabled={isLoading}>
                  {isLoading ? 'Updating...' : 'Update Profile'}
                </button>
              </div>
            </div>
          </form>

          {message && (
            <div className={`toast ${message.includes('Error') ? 'err' : 'ok'}`} style={{ 
              display: 'block', 
              position: 'relative', 
              margin: '16px 0 0 0',
              background: message.includes('Error') ? 'var(--err)' : 'var(--ok)'
            }}>
              {message}
            </div>
          )}
        </div>

        <div className="card" style={{ flex: '1 1 300px' }}>
          <h3 style={{ margin: '0 0 6px 0' }}>About Locations</h3>
          <div className="divider"></div>
          <div className="muted" style={{ fontSize: '14px' }}>
            <p><strong>For Clients:</strong> Your location helps us find lawyers nearby and show accurate distances.</p>
            <p><strong>For Lawyers:</strong> Clients searching in your area will be able to find you more easily.</p>
            <p><strong>Privacy:</strong> Your exact coordinates are not shared. Only approximate distance calculations are used.</p>
          </div>
          
          <div className="divider"></div>
          
          <div className="list">
            <a className="item" href="/chat">
              <div>
                <b>Open Chat</b>
                <div className="footnote">Start conversations with the AI assistant</div>
              </div>
              <span className="badge">Chat</span>
            </a>
            <a className="item" href="/dashboard">
              <div>
                <b>Back to Dashboard</b>
                <div className="footnote">Find lawyers or manage your account</div>
              </div>
              <span className="badge">Dashboard</span>
            </a>
          </div>
        </div>
      </div>
    </Layout>
  );
};