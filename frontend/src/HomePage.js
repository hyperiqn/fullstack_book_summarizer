// frontend/src/HomePage.js
import React from 'react';
import { Link } from 'react-router-dom';

function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-50 text-gray-800">
      <div className="bg-white p-8 rounded-lg shadow-lg text-center max-w-md w-full">
        <h2 className="text-3xl font-bold mb-4 text-blue-600">Welcome to Book Summarizer!</h2>
        <p className="text-lg mb-6">Your AI-powered book summarization and chat interface.</p>
        <p className="text-md text-gray-600 mb-8">
          Please <Link to="/login" className="text-blue-600 hover:underline font-medium">Login</Link> or{' '}
          <Link to="/register" className="text-blue-600 hover:underline font-medium">Register</Link> to get started.
        </p>
      </div>
    </div>
  );
}

export default HomePage;