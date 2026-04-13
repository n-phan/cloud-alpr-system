import { useState } from 'react';
import { handleSignIn, handleSignUp } from '../services/auth';
import '../styles/Login.css';

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      if (isSignUp) {
        await handleSignUp(email, password);
        setMessage('Sign up successful! Please verify your email and sign in.');
        setEmail('');
        setPassword('');
        setTimeout(() => setIsSignUp(false), 2000);
      } else {
        await handleSignIn(email, password);
        setMessage('Sign in successful!');
        setTimeout(() => onLoginSuccess(), 1000);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>ALPR Parking System</h1>
        <h2>{isSignUp ? 'Sign Up' : 'Sign In'}</h2>

        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Processing...' : isSignUp ? 'Sign Up' : 'Sign In'}
          </button>
        </form>

        {error && <p className="error-message">{error}</p>}
        {message && <p className="success-message">{message}</p>}

        <p className="toggle-mode">
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}
          <button
            type="button"
            onClick={() => setIsSignUp(!isSignUp)}
            className="toggle-button"
          >
            {isSignUp ? 'Sign In' : 'Sign Up'}
          </button>
        </p>

        <div className="test-credentials">
          <p><strong>Test Credentials:</strong></p>
          <p>Email: newuser@example.com</p>
          <p>Password: Test123!@</p>
	  <p>Email: admin@example.com</p>
	  <p>Password: Admin123!@</p>
          <p style={{ fontSize: '0.8rem', color: '#999' }}>
            (Must be verified in Cognito first)
          </p>
        </div>
      </div>
    </div>
  );
}
