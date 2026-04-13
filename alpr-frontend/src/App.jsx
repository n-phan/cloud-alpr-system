import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { getAuthenticatedUser, handleSignOut, isUserAdmin } from './services/auth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Admin from './pages/Admin';
import ProtectedRoute from './components/ProtectedRoute';
import './styles/App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const currentUser = await getAuthenticatedUser();
      if (currentUser) {
        const admin = await isUserAdmin();
        setUser({
          ...currentUser,
          isAdmin: admin
        });
      } else {
        setUser(null);
      }
    } catch (err) {
      console.log('Not authenticated');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await handleSignOut();
      setUser(null);
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <BrowserRouter>
      {user && (
        <header className="app-header">
          <div className="header-content">
            <h1>ALPR Parking System</h1>
            <div className="header-user">
              <span className="user-email">{user.email}</span>
              {user.isAdmin && <span className="user-badge">Admin</span>}
              <button onClick={handleLogout} className="logout-button">
                Logout
              </button>
            </div>
          </div>
        </header>
      )}

      <main className={user ? 'app-content' : ''}>
        <Routes>
          <Route path="/" element={user ? <Navigate to="/dashboard" /> : <Login onLoginSuccess={checkAuth} />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute user={user}>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute user={user} requireAdmin={true}>
                <Admin />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
