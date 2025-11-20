import axios, { AxiosInstance, AxiosError } from 'axios';

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
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
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

// Project interface
export interface Project {
  projectId: string;
  userId: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  s3Key?: string;
  floorspaceUrl?: string;
}

// API methods
export const api = {
  // List all projects for the authenticated user
  listProjects: async (): Promise<Project[]> => {
    const response = await apiClient.get<{ projects: Project[] }>('/GET/projects');
    return response.data.projects;
  },

  // Get a specific project
  getProject: async (projectId: string): Promise<Project> => {
    const response = await apiClient.get<Project>(`/projects/${projectId}`);
    return response.data;
  },

  // Create or update a project
  createUpdateProject: async (
    projectId: string,
    data: { name: string; description?: string }
  ): Promise<Project> => {
    const response = await apiClient.post<Project>(`/projects/${projectId}`, data);
    return response.data;
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
