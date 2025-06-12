// frontend/src/App.js
import React from 'react';
import './index.css'; 
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';

import RegisterPage from './RegisterPage';
import LoginPage from './LoginPage';
import DocumentsPage from './DocumentsPage';
import HomePage from './HomePage'; 

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/documents"
            element={
              <ProtectedRoute>
                <DocumentsPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;