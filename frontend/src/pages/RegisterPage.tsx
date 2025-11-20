import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { signUp, confirmSignUp } from 'aws-amplify/auth';
import { DevModeBanner } from '../components/DevModeBanner';
import './RegisterPage.css';

interface FormErrors {
  firstName?: string;
  lastName?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  confirmationCode?: string;
  general?: string;
}

export const RegisterPage = () => {
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [confirmationCode, setConfirmationCode] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validatePassword = (password: string): boolean => {
    // Password must be at least 8 characters with uppercase, lowercase, and numbers
    const minLength = password.length >= 8;
    const hasUppercase = /[A-Z]/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    const hasNumber = /\d/.test(password);
    
    return minLength && hasUppercase && hasLowercase && hasNumber;
  };

  const validateInput = (): boolean => {
    const newErrors: FormErrors = {};

    if (!firstName) {
      newErrors.firstName = 'First name is required';
    }

    if (!lastName) {
      newErrors.lastName = 'Last name is required';
    }

    if (!email) {
      newErrors.email = 'Email is required';
    } else if (!validateEmail(email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    } else if (!validatePassword(password)) {
      newErrors.password = 'Password must be at least 8 characters with uppercase, lowercase, and numbers';
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!validateInput()) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      await signUp({
        username: email,
        password: password,
        options: {
          userAttributes: {
            email: email,
            given_name: firstName,
            family_name: lastName,
          },
          autoSignIn: false,
        },
      });

      // Registration successful, show confirmation code input
      setShowConfirmation(true);
      setErrors({});
      console.log('Registration successful! Check your email for verification code.');
    } catch (error: any) {
      console.error('Registration error:', error);
      console.error('Error name:', error.name);
      console.error('Error message:', error.message);
      
      const newErrors: FormErrors = {};
      
      if (error.name === 'UsernameExistsException') {
        newErrors.general = 'An account with this email already exists';
      } else if (error.name === 'InvalidPasswordException') {
        newErrors.password = 'Password must be at least 8 characters with uppercase, lowercase, and numbers';
      } else if (error.name === 'InvalidParameterException') {
        // Show the actual Cognito error message for debugging
        newErrors.general = error.message || 'Invalid email or password format';
      } else {
        newErrors.general = error.message || 'Registration failed. Please try again.';
      }
      
      setErrors(newErrors);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmation = async (e: FormEvent) => {
    e.preventDefault();

    if (!confirmationCode) {
      setErrors({ confirmationCode: 'Verification code is required' });
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      await confirmSignUp({
        username: email,
        confirmationCode: confirmationCode,
      });

      // Confirmation successful, redirect to login
      navigate('/login', { 
        state: { 
          message: 'Email verified successfully! You can now log in.' 
        } 
      });
    } catch (error: any) {
      console.error('Confirmation error:', error);
      
      const newErrors: FormErrors = {};
      
      if (error.name === 'CodeMismatchException') {
        newErrors.confirmationCode = 'Invalid verification code. Please try again.';
      } else if (error.name === 'ExpiredCodeException') {
        newErrors.confirmationCode = 'Verification code has expired. Please request a new one.';
      } else {
        newErrors.general = error.message || 'Verification failed. Please try again.';
      }
      
      setErrors(newErrors);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="register-page">
      <div className="register-container">
        <h1>{showConfirmation ? 'Verify Your Email' : 'Create Account'}</h1>
        <p>{showConfirmation ? 'Enter the verification code sent to your email' : 'Sign up to start creating floorplans'}</p>
        
        <DevModeBanner />
        
        {showConfirmation ? (
          <form onSubmit={handleConfirmation} className="register-form">
            {errors.general && (
              <div className="error-message general-error">
                {errors.general}
              </div>
            )}

            <div className="success-message" style={{ marginBottom: '20px' }}>
              A verification code has been sent to <strong>{email}</strong>
            </div>

            <div className="form-group">
              <label htmlFor="confirmationCode">Verification Code</label>
              <input
                id="confirmationCode"
                type="text"
                value={confirmationCode}
                onChange={(e) => setConfirmationCode(e.target.value)}
                placeholder="Enter 6-digit code"
                disabled={isLoading}
                maxLength={6}
              />
              {errors.confirmationCode && (
                <span className="error-message">{errors.confirmationCode}</span>
              )}
            </div>

            <button 
              type="submit" 
              className="submit-button"
              disabled={isLoading}
            >
              {isLoading ? 'Verifying...' : 'Verify Email'}
            </button>

            <div style={{ marginTop: '15px', textAlign: 'center', fontSize: '14px', color: '#666' }}>
              Didn't receive the code? Check your spam folder or{' '}
              <button 
                type="button"
                onClick={() => setShowConfirmation(false)}
                style={{ 
                  background: 'none', 
                  border: 'none', 
                  color: '#4CAF50', 
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0,
                  font: 'inherit'
                }}
              >
                try again
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="register-form">
          {errors.general && (
            <div className="error-message general-error">
              {errors.general}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="firstName">First Name</label>
            <input
              id="firstName"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="Enter your first name"
              disabled={isLoading}
            />
            {errors.firstName && (
              <span className="error-message">{errors.firstName}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="lastName">Last Name</label>
            <input
              id="lastName"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Enter your last name"
              disabled={isLoading}
            />
            {errors.lastName && (
              <span className="error-message">{errors.lastName}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              disabled={isLoading}
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
            />
            {errors.password && (
              <span className="error-message">{errors.password}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm your password"
              disabled={isLoading}
            />
            {errors.confirmPassword && (
              <span className="error-message">{errors.confirmPassword}</span>
            )}
          </div>

          <button 
            type="submit" 
            className="submit-button"
            disabled={isLoading}
          >
            {isLoading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>
        )}

        {!showConfirmation && (
          <div className="login-link">
            Already have an account? <a href="/login">Log in</a>
          </div>
        )}
      </div>
    </div>
  );
};

export default RegisterPage;
