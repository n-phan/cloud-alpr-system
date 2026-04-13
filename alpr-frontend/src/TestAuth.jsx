import { useState } from 'react';
import { handleSignUp, handleSignIn } from './services/auth';

export default function TestAuth() {
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);

  const testSignUp = async () => {
    setError(null);
    setStatus('Signing up...');
    try {
      const result = await handleSignUp('newuser@example.com', 'Test123!@');
      console.log('Sign up result:', result);
      setStatus('✅ Sign up successful! Check console for confirmation code.');
    } catch (err) {
      console.error('Error:', err);
      setError(err.message);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial' }}>
      <h1>Auth Test</h1>
      
      {error && (
        <div style={{ color: 'white', background: '#cc0000', padding: '10px', borderRadius: '5px', marginBottom: '10px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      
      {status && (
        <div style={{ color: 'white', background: '#0066cc', padding: '10px', borderRadius: '5px', marginBottom: '10px' }}>
          {status}
        </div>
      )}
      
      <button onClick={testSignUp} style={{ padding: '10px 20px', cursor: 'pointer' }}>
        Test Sign Up
      </button>
    </div>
  );
}
