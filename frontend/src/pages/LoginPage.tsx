import { useState, FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { signIn } from 'aws-amplify/auth';
import { useAuth } from '../contexts/AuthContext';
import { DevModeBanner } from '../components/DevModeBanner';
import './LoginPage.css';

interface FormErrors {
  email?: string;
  password?: string;
  general?: string;
}

interface LocationState {
  message?: string;
}

export const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState;
  const { checkAuth } = useAuth();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage] = useState(state?.message || '');

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    const newErrors: FormErrors = {};
    if (!email) {
      newErrors.email = 'Email is required';
    }
    if (!password) {
      newErrors.password = 'Password is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      const { isSignedIn, nextStep } = await signIn({
        username: email,
        password: password,
      });

      if (isSignedIn) {
        // Get the current session to extract the JWT token
        const { fetchAuthSession } = await import('aws-amplify/auth');
        const session = await fetchAuthSession();
        
        if (session.tokens?.idToken) {
          // Store JWT token in localStorage
          localStorage.setItem('authToken', session.tokens.idToken.toString());
          localStorage.setItem('userId', session.tokens.idToken.payload.sub as string);
          
          // Update auth context state
          await checkAuth();
          
          // Redirect to dashboard
          navigate('/dashboard');
        }
      } else if (nextStep.signInStep === 'CONFIRM_SIGN_UP') {
        setErrors({ general: 'Please verify your email before logging in.' });
      } else {
        setErrors({ general: 'Authentication incomplete. Please try again.' });
      }
    } catch (error: any) {
      console.error('Login error:', error);
      
      const newErrors: FormErrors = {};
      
      if (error.name === 'NotAuthorizedException' || error.name === 'UserNotFoundException') {
        newErrors.general = 'Invalid email or password';
      } else if (error.name === 'UserNotConfirmedException') {
        newErrors.general = 'Please verify your email before logging in';
      } else if (error.name === 'NetworkError') {
        newErrors.general = 'Unable to connect. Please check your internet connection.';
      } else {
        newErrors.general = error.message || 'Login failed. Please try again.';
      }
      
      setErrors(newErrors);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>Welcome Back</h1>
        <p>Sign in to access your floorplans</p>
        
        <DevModeBanner />
        
        {successMessage && (
          <div className="success-message">
            {successMessage}
          </div>
        )}

        <form onSubmit={handleLogin} className="login-form">
          {errors.general && (
            <div className="error-message general-error">
              {errors.general}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              disabled={isLoading}
              autoComplete="email"
            />
            {errors.email && (
              <span className="error-message">{errors.email}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              disabled={isLoading}
              autoComplete="current-password"
            />
            {errors.password && (
              <span className="error-message">{errors.password}</span>
            )}
          </div>

          <button 
            type="submit" 
            className="submit-button"
            disabled={isLoading}
          >
            {isLoading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <div className="register-link">
          Don't have an account? <a href="/register">Sign up</a>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
