import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { getAuthenticatedUser, handleSignOut, isUserAdmin } from './services/auth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Admin from './pages/Admin';
import Citations from './pages/Citations';
import ProtectedRoute from './components/ProtectedRoute';
import './styles/App.css';

function AppHeader({ user, onLogout }) {
  const { pathname } = useLocation();
  const isAdminPage = pathname === '/admin';

  return (
    <header className="app-header">
      <div className="header-content">
        <h1>ALPR Parking System</h1>
        <div className="header-user">
          <span className="user-email">{user.email}</span>
          {user.isAdmin && (
            <Link to={isAdminPage ? '/dashboard' : '/admin'} className="user-badge">
              {isAdminPage ? 'Dashboard' : 'Admin'}
            </Link>
          )}
          <button onClick={onLogout} className="logout-button">
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}

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
      {user && <AppHeader user={user} onLogout={handleLogout} />}

      <main className={user ? 'app-content' : ''}>
        <Routes>
          <Route path="/" element={<Citations />} />
          <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <Login onLoginSuccess={checkAuth} />} />
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
