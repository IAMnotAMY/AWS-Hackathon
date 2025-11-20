import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { getCurrentUser, signOut as amplifySignOut, fetchAuthSession } from 'aws-amplify/auth';

interface AuthContextType {
  isAuthenticated: boolean;
  userId: string | null;
  loading: boolean;
  signOut: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      // Check if user is authenticated
      const user = await getCurrentUser();
      
      if (user) {
        // Get the session to extract userId
        const session = await fetchAuthSession();
        const sub = session.tokens?.idToken?.payload.sub as string;
        
        setIsAuthenticated(true);
        setUserId(sub || null);
        
        // Update localStorage
        if (session.tokens?.idToken) {
          localStorage.setItem('authToken', session.tokens.idToken.toString());
          localStorage.setItem('userId', sub);
        }
      } else {
        setIsAuthenticated(false);
        setUserId(null);
        localStorage.removeItem('authToken');
        localStorage.removeItem('userId');
      }
    } catch (error: any) {
      // User is not authenticated or Cognito not configured
      if (error.message?.includes('Auth UserPool not configured')) {
        console.warn('Cognito not configured - running in development mode');
      }
      setIsAuthenticated(false);
      setUserId(null);
      localStorage.removeItem('authToken');
      localStorage.removeItem('userId');
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      await amplifySignOut();
      setIsAuthenticated(false);
      setUserId(null);
      localStorage.removeItem('authToken');
      localStorage.removeItem('userId');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const value: AuthContextType = {
    isAuthenticated,
    userId,
    loading,
    signOut,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
