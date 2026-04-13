import { Navigate } from 'react-router-dom';

export default function ProtectedRoute({ children, user, requireAdmin = false }) {
  if (!user) {
    return <Navigate to="/" />;
  }

  if (requireAdmin && !user.isAdmin) {
    return <Navigate to="/dashboard" />;
  }

  return children;
}
