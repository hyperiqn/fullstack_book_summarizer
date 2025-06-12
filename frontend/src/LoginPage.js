// frontend/src/LoginPage.js
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (event) => {
    event.preventDefault();
    setMessage('');

    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    try {
      const response = await fetch('http://localhost:8001/api/v1/auth/token', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('access_token', data.access_token);
        setMessage('Login successful!');
        console.log('Login success:', data);
        navigate('/documents');
      } else {
        const errorData = await response.json();
        setMessage(`Login failed: ${errorData.detail || 'Invalid credentials'}`);
        console.error('Login failed:', errorData);
      }
    } catch (error) {
      setMessage(`An error occurred: ${error.message}`);
      console.error('Network error or unexpected issue:', error);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-50 text-gray-800">
      <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full"> {/* Card wrapper */}
        <h2 className="text-3xl font-bold mb-6 text-center text-blue-600">Login</h2>
        <form onSubmit={handleLogin} className="space-y-4"> {/* Tailwind form spacing */}
          <div className="form-group">
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email:</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="off"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="off"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            />
          </div>
          <button type="submit" className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
            Login
          </button>
        </form>
        {message && <p className="mt-4 text-center text-sm font-medium text-red-600">{message}</p>}
        <p className="mt-6 text-center text-sm text-gray-600">
          Don't have an account? <Link to="/register" className="font-medium text-blue-600 hover:underline">Register here</Link>.
        </p>
      </div>
    </div>
  );
}

export default LoginPage;