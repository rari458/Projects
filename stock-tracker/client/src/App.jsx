// client/src/App.jsx

import React, { useContext } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthContext } from './context/AuthContext.jsx';
import Auth from './pages/Auth.jsx';
import Dashboard from './pages/Dashboard.jsx';
import AuthCallback from './pages/AuthCallback.jsx';
import './App.css';

function App() {
  const { user, loading } = useContext(AuthContext);

  const ProtectedRoute = ({ children }) => {
    if (loading) {
      return <div className="loading-container"><h2>로딩 중...</h2></div>;
    }
    return user ? children : <Navigate to="/login" replace />;
  };

  const LoginRoute = ({ children }) => {
    if (loading) {
      return <div className="loading-container"><h2>로딩 중...</h2></div>;
    }
    return user ? <Navigate to="/" replace /> : children;
  };

  return (
    <Routes>
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/login"
        element={
          <LoginRoute>
            <Auth />
          </LoginRoute>
        }
      />
      <Route
        path="/auth/callback"
        element={<AuthCallback />}
      />    
    </Routes>
  );
}

export default App;