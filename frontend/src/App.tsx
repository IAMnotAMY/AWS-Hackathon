import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Amplify } from 'aws-amplify';
import { awsConfig } from './aws-config';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import RegisterPage from './pages/RegisterPage';
import LoginPage from './pages/LoginPage';
import ProjectDashboard from './pages/ProjectDashboard';
import FloorspaceEditorPage from './pages/FloorspaceEditorPage';
import { verifyAwsConfig } from './utils/verifyConfig';

// Verify and configure Amplify
verifyAwsConfig();

try {
  Amplify.configure(awsConfig);
} catch (error) {
  console.warn('Amplify configuration warning:', error);
  console.info('To use authentication, deploy the infrastructure and set VITE_USER_POOL_ID and VITE_USER_POOL_CLIENT_ID environment variables');
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<LoginPage />} />
          
          {/* Protected routes */}
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <ProjectDashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/editor/:projectId" 
            element={
              <ProtectedRoute>
                <FloorspaceEditorPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Catch all - redirect to login */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
