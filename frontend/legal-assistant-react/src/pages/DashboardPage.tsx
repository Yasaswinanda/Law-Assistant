import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Layout } from '../components/Layout';

interface Lawyer {
  id: number;
  email: string;
  role: string;
  location_name?: string;
  location_lat?: number;
  location_lon?: number;
  distance_km?: number;
}

export const DashboardPage: React.FC = () => {
  const { user, token } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [radius, setRadius] = useState('50');
  const [lawyers, setLawyers] = useState<Lawyer[]>([]);
  const [userLocation, setUserLocation] = useState<{ lat?: number; lon?: number }>({});
  const [geoInfo, setGeoInfo] = useState('No location yet');
  const [isLoading, setIsLoading] = useState(false);

  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';

  const handleUseGeo = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setUserLocation({ lat: latitude, lon: longitude });
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

  const searchLawyers = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('q', searchQuery);
      if (userLocation.lat && userLocation.lon) {
        params.append('lat', userLocation.lat.toString());
        params.append('lon', userLocation.lon.toString());
        params.append('radius_km', radius);
      }

      const response = await fetch(`${API_BASE}/lawyers?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setLawyers(data.lawyers);
      }
    } catch (error) {
      console.error('Error searching lawyers:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const startConversation = (lawyerId: number) => {
    window.location.href = `/chat?with_user_id=${lawyerId}`;
  };

  const testLawyerAccess = async () => {
    try {
      const response = await fetch(`${API_BASE}/lawyer/dashboard`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        alert(`Success: ${data.message}`);
      } else {
        const error = await response.json();
        alert(`Error: ${error.error}`);
      }
    } catch (error) {
      alert('Error: Failed to test lawyer access');
    }
  };

  return (
    <Layout currentPage="dashboard">
      <div className="row">
        {/* Client: Discover Lawyers */}
        {user?.role === 'client' && (
          <div className="card" style={{ flex: '1 1 300px' }}>
            <h2 style={{ margin: '0 0 6px 0' }}>Discover Lawyers</h2>
            <p className="muted">Find verified lawyers. Use your location to see who's nearby.</p>
            <div className="divider"></div>
            <div className="grid" style={{ gridTemplateColumns: '2fr 1fr auto', alignItems: 'end' }}>
              <div className="field">
                <label>Search</label>
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Name, email, city"
                />
              </div>
              <div className="field">
                <label>Radius (km)</label>
                <input
                  type="number"
                  min="1"
                  max="500"
                  value={radius}
                  onChange={(e) => setRadius(e.target.value)}
                />
              </div>
              <div className="row">
                <button className="btn" onClick={handleUseGeo}>
                  Use my location
                </button>
                <button className="btn prime" onClick={searchLawyers} disabled={isLoading}>
                  {isLoading ? 'Searching...' : 'Find'}
                </button>
              </div>
            </div>
            <div className="spacer"></div>
            <div className="footnote">{geoInfo}</div>
            <div className="divider"></div>
            <div className="list">
              {lawyers.map((lawyer) => (
                <div key={lawyer.id} className="item">
                  <div>
                    <div><b>{lawyer.email}</b></div>
                    <div className="footnote">
                      {lawyer.location_name && `${lawyer.location_name} • `}
                      {lawyer.distance_km && `${lawyer.distance_km} km away`}
                    </div>
                  </div>
                  <button className="btn prime" onClick={() => startConversation(lawyer.id)}>
                    Contact
                  </button>
                </div>
              ))}
              {lawyers.length === 0 && !isLoading && (
                <div className="muted">No lawyers found. Try adjusting your search criteria.</div>
              )}
            </div>
          </div>
        )}

        {/* Lawyer: Welcome Card */}
        {user?.role === 'lawyer' && (
          <div className="card" style={{ flex: '1 1 300px' }}>
            <h2 style={{ margin: '0 0 6px 0' }}>Welcome, Lawyer</h2>
            <div className="divider"></div>
            <p className="muted">
              Clients will contact you directly. Use the Chat panel to view ongoing conversations.
            </p>
            <div className="row">
              <a className="btn prime" href="/chat">Open Chat</a>
              <a className="btn" href="/profile">Update Profile</a>
            </div>
          </div>
        )}

        <div className="card" style={{ flex: '1 1 260px' }}>
          <h2 style={{ margin: '0 0 6px 0' }}>Quick Actions</h2>
          <div className="divider"></div>
          <div className="list">
            <a className="item" href="/chat">
              <div>
                <b>Open Chat</b>
                <div className="footnote">AI Assistant & direct messaging.</div>
              </div>
              <span className="badge">Chat</span>
            </a>
            <a className="item" href="/profile">
              <div>
                <b>Update your profile</b>
                <div className="footnote">Location helps matching nearby lawyers (for clients).</div>
              </div>
              <span className="badge">Profile</span>
            </a>
            {user?.role === 'lawyer' && (
              <button className="item btn" onClick={testLawyerAccess}>
                <div>
                  <b>Lawyer portal check</b>
                  <div className="footnote">Verifies access (lawyers only)</div>
                </div>
                <span className="badge">Test</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};