import axios, { AxiosInstance, AxiosError } from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';

// API client configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://api.example.com';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  async (config) => {
    try {
      // Get fresh token from Amplify
      const session = await fetchAuthSession();
      const idToken = session.tokens?.idToken?.toString();
      const accessToken = session.tokens?.accessToken?.toString();
      
      console.log('🔐 Auth Debug Info:');
      console.log('ID Token exists:', !!idToken);
      console.log('Access Token exists:', !!accessToken);
      console.log('ID Token (first 50 chars):', idToken?.substring(0, 50));
      console.log('Access Token (first 50 chars):', accessToken?.substring(0, 50));
      console.log('ID Token Payload:', session.tokens?.idToken?.payload);
      console.log('Access Token Payload:', session.tokens?.accessToken?.payload);
      
      // Use ID token with Bearer prefix (standard format)
      if (idToken) {
        config.headers.Authorization = `${idToken}`;
        console.log('✅ Using ID Token with Bearer prefix');
      } else {
        console.warn('⚠️ No ID token available');
      }
    } catch (error) {
      console.error('❌ Error fetching auth token:', error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear auth and redirect to login
      localStorage.removeItem('authToken');
      localStorage.removeItem('userId');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Project interface matching DB schema
export interface Project {
  ProjectID: string;
  UserID: string;
  ProjectName: string;
  Description?: string;
  CreatedTime: string;
  UpdatedTime: string;
  S3Key?: string;
  floorspaceUrl?: string;
}

// Helper to convert DB format to display format
export const formatProject = (dbProject: Project) => ({
  projectId: dbProject.ProjectID,
  userId: dbProject.UserID,
  name: dbProject.ProjectName,
  description: dbProject.Description,
  createdAt: new Date(typeof dbProject.CreatedTime === 'number' 
    ? dbProject.CreatedTime * 1000 
    : dbProject.CreatedTime).toLocaleDateString(),
  updatedAt: new Date(typeof dbProject.UpdatedTime === 'number' 
    ? dbProject.UpdatedTime * 1000 
    : dbProject.UpdatedTime).toLocaleDateString(),
});

// API methods
export const api = {
  // List all projects for the authenticated user
  listProjects: async (): Promise<Project[]> => {
    // Get username from token
    const session = await fetchAuthSession();
    const username = session.tokens?.idToken?.payload['cognito:username'] || 
                     session.tokens?.idToken?.payload.email ||
                     'unknown';
    
    // Send GET request with username as query parameter
    const response = await apiClient.get('/project', {
      params: {
        username: username
      }
    });
    
    console.log('📦 Raw API Response:', response.data);
    
    // Handle both Lambda proxy response and direct response
    let data = response.data;
    
    // If response has statusCode and body, it's a raw Lambda response
    if (data.statusCode && data.body) {
      console.log('🔄 Parsing Lambda proxy response body');
      data = JSON.parse(data.body);
    }
    
    console.log('📦 Parsed data:', data);
    
    // Return projects array (handle multiple possible keys)
    const projects = data.projects || data.items || data.Projects || data.Items || [];
    console.log('✅ Returning projects:', projects);
    
    return projects;
  },

  // Get a specific project
  getProject: async (projectId: string): Promise<Project> => {
    // Get username from token
    const session = await fetchAuthSession();
    const username = session.tokens?.idToken?.payload['cognito:username'] || 
                     session.tokens?.idToken?.payload.email ||
                     'unknown';
    
    const response = await apiClient.get(`/project/${projectId}`, {
      params: {
        username: username
      }
    });
    
    // Handle both Lambda proxy response and direct response
    let data = response.data;
    
    // If response has statusCode and body, it's a raw Lambda response
    if (data.statusCode && data.body) {
      data = JSON.parse(data.body);
    }
    
    return data.project || data;
  },

  // Create or update a project
  createUpdateProject: async (
    projectId: string,
    data: { name: string; description?: string }
  ): Promise<Project> => {
    // Get username from token
    const session = await fetchAuthSession();
    const username = session.tokens?.idToken?.payload['cognito:username'] || 
                     session.tokens?.idToken?.payload.email ||
                     'unknown';
    
    const response = await apiClient.post('/project', {
      projectName: data.name
    }, {
      params: {
        username: username
      }
    });
    
    console.log('📦 Create Project Response:', response.data);
    
    // Handle both Lambda proxy response and direct response
    let responseData = response.data;
    
    // If response has statusCode and body, it's a raw Lambda response
    if (responseData.statusCode && responseData.body) {
      responseData = JSON.parse(responseData.body);
    }
    
    return responseData.project || responseData;
  },

  // Delete a project
  deleteProject: async (projectId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}`);
  },

  // Upload floorspace JSON
  uploadFloorspace: async (
    projectId: string,
    floorspaceJson: any
  ): Promise<{ success: boolean; updatedAt: string }> => {
    const response = await apiClient.post(`/projects/${projectId}/upload`, {
      floorspaceJson,
    });
    return response.data;
  },
};

export default apiClient;
