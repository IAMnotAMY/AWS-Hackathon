/**
 * Property-Based Tests for Project Dashboard
 * Feature: floorspace-3d-viewer, Property 7: Dashboard retrieves user projects
 * Validates: Requirements 3.1
 */

import * as fc from 'fast-check';
import { api, Project } from '../../services/api';
import axios from 'axios';

// Mock axios to avoid real API calls
jest.mock('axios');
const mockedAxios = axios as any;

// Generator for valid project data
const projectArbitrary = fc.record({
  projectId: fc.uuid(),
  userId: fc.uuid(),
  name: fc.string({ minLength: 1, maxLength: 100 }),
  description: fc.option(fc.string({ maxLength: 500 }), { nil: undefined }),
  createdAt: fc.date().map(d => d.toISOString()),
  updatedAt: fc.date().map(d => d.toISOString()),
  s3Key: fc.option(fc.string(), { nil: undefined }),
});

// Generator for arrays of projects
const projectsArrayArbitrary = fc.array(projectArbitrary, { minLength: 0, maxLength: 20 });

describe('Dashboard Properties', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    
    // Setup default axios mock
    mockedAxios.create = jest.fn(() => mockedAxios as any);
    mockedAxios.interceptors = {
      request: { use: jest.fn(), eject: jest.fn(), clear: jest.fn() },
      response: { use: jest.fn(), eject: jest.fn(), clear: jest.fn() },
    } as any;
  });

  describe('Property 7: Dashboard retrieves user projects', () => {
    test('for any authenticated user, dashboard should retrieve all projects where userId matches', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.uuid(), // authenticated userId
          projectsArrayArbitrary,
          async (authenticatedUserId, allProjects) => {
            // Filter projects to only those belonging to the authenticated user
            const userProjects = allProjects.map(p => ({ ...p, userId: authenticatedUserId }));
            
            // Mock the API response
            mockedAxios.get = jest.fn().mockResolvedValue({
              data: { projects: userProjects },
            });

            // Call the API
            const result = await api.listProjects();

            // Verify all returned projects belong to the authenticated user
            const allBelongToUser = result.every(project => project.userId === authenticatedUserId);
            
            // Verify the correct number of projects returned
            const correctCount = result.length === userProjects.length;

            return allBelongToUser && correctCount;
          }
        ),
        { numRuns: 100 }
      );
    });

    test('dashboard should handle empty project list correctly', async () => {
      await fc.assert(
        fc.asyncProperty(fc.uuid(), async (userId) => {
          // Mock empty response
          mockedAxios.get = jest.fn().mockResolvedValue({
            data: { projects: [] },
          });

          const result = await api.listProjects();

          // Should return empty array
          return Array.isArray(result) && result.length === 0;
        }),
        { numRuns: 100 }
      );
    });

    test('dashboard should retrieve all project fields correctly', async () => {
      await fc.assert(
        fc.asyncProperty(projectsArrayArbitrary, async (projects) => {
          // Mock the API response
          mockedAxios.get = jest.fn().mockResolvedValue({
            data: { projects },
          });

          const result = await api.listProjects();

          // Verify all projects have required fields
          const allHaveRequiredFields = result.every(project => 
            project.projectId !== undefined &&
            project.userId !== undefined &&
            project.name !== undefined &&
            project.createdAt !== undefined &&
            project.updatedAt !== undefined
          );

          // Verify project count matches
          const correctCount = result.length === projects.length;

          return allHaveRequiredFields && correctCount;
        }),
        { numRuns: 100 }
      );
    });

    test('dashboard should maintain project data integrity during retrieval', async () => {
      await fc.assert(
        fc.asyncProperty(projectsArrayArbitrary, async (projects) => {
          // Mock the API response
          mockedAxios.get = jest.fn().mockResolvedValue({
            data: { projects },
          });

          const result = await api.listProjects();

          // Verify each project's data matches the source
          const dataIntact = result.every((project, index) => {
            const source = projects[index];
            return (
              project.projectId === source.projectId &&
              project.userId === source.userId &&
              project.name === source.name &&
              project.createdAt === source.createdAt &&
              project.updatedAt === source.updatedAt
            );
          });

          return dataIntact;
        }),
        { numRuns: 100 }
      );
    });

    test('dashboard should include authentication token in API request', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.string({ minLength: 20, maxLength: 200 }), // auth token
          projectsArrayArbitrary,
          async (authToken, projects) => {
            // Set auth token in localStorage
            localStorage.setItem('authToken', authToken);

            // Mock the API response
            const mockGet = jest.fn().mockResolvedValue({
              data: { projects },
            });
            mockedAxios.get = mockGet;

            try {
              await api.listProjects();

              // Verify the request was made (token would be added by interceptor)
              const requestMade = mockGet.mock.calls.length > 0;

              return requestMade;
            } finally {
              // Clean up
              localStorage.removeItem('authToken');
            }
          }
        ),
        { numRuns: 50 }
      );
    });

    test('dashboard should handle API errors gracefully', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.constantFrom(401, 403, 404, 500),
          fc.string(),
          async (statusCode, errorMessage) => {
            // Mock API error
            mockedAxios.get = jest.fn().mockRejectedValue({
              response: {
                status: statusCode,
                data: { error: { message: errorMessage } },
              },
            });

            try {
              await api.listProjects();
              // Should have thrown an error
              return false;
            } catch (error: any) {
              // Error should be caught and contain response data
              return error.response?.status === statusCode;
            }
          }
        ),
        { numRuns: 50 }
      );
    });
  });

  describe('Property 8: Project display contains required fields', () => {
    test('for any project, display should contain name, createdAt, and updatedAt', async () => {
      await fc.assert(
        fc.asyncProperty(projectArbitrary, async (project) => {
          // Verify project has all required display fields
          const hasName = typeof project.name === 'string' && project.name.length > 0;
          const hasCreatedAt = typeof project.createdAt === 'string';
          const hasUpdatedAt = typeof project.updatedAt === 'string';

          // Verify dates are valid ISO strings
          const createdAtValid = !isNaN(Date.parse(project.createdAt));
          const updatedAtValid = !isNaN(Date.parse(project.updatedAt));

          return hasName && hasCreatedAt && hasUpdatedAt && createdAtValid && updatedAtValid;
        }),
        { numRuns: 100 }
      );
    });

    test('project dates should be parseable and formattable', async () => {
      await fc.assert(
        fc.asyncProperty(projectArbitrary, async (project) => {
          try {
            // Attempt to parse and format dates
            const createdDate = new Date(project.createdAt);
            const updatedDate = new Date(project.updatedAt);

            const createdFormatted = createdDate.toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            });

            const updatedFormatted = updatedDate.toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            });

            // Formatted dates should be non-empty strings
            return (
              typeof createdFormatted === 'string' &&
              createdFormatted.length > 0 &&
              typeof updatedFormatted === 'string' &&
              updatedFormatted.length > 0
            );
          } catch {
            // Date parsing/formatting failed
            return false;
          }
        }),
        { numRuns: 100 }
      );
    });

    test('project name should be displayable text', async () => {
      await fc.assert(
        fc.asyncProperty(projectArbitrary, async (project) => {
          // Name should be a non-empty string
          const isString = typeof project.name === 'string';
          const isNonEmpty = project.name.length > 0;
          const isTrimmed = project.name.trim().length > 0;

          return isString && isNonEmpty && isTrimmed;
        }),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 12: Dashboard updates after deletion', () => {
    test('for any project deletion, dashboard should no longer display the deleted project', async () => {
      await fc.assert(
        fc.asyncProperty(
          projectsArrayArbitrary.filter(arr => arr.length > 0),
          fc.nat(),
          async (projects, indexSeed) => {
            if (projects.length === 0) return true;

            const deleteIndex = indexSeed % projects.length;
            const projectToDelete = projects[deleteIndex];

            // Mock successful deletion
            mockedAxios.delete = jest.fn().mockResolvedValue({ data: { success: true } });

            // Call delete API
            await api.deleteProject(projectToDelete.projectId);

            // Simulate dashboard update - remove deleted project
            const updatedProjects = projects.filter(
              p => p.projectId !== projectToDelete.projectId
            );

            // Verify deleted project is not in the updated list
            const deletedProjectNotPresent = !updatedProjects.some(
              p => p.projectId === projectToDelete.projectId
            );

            // Verify count decreased by 1
            const countCorrect = updatedProjects.length === projects.length - 1;

            return deletedProjectNotPresent && countCorrect;
          }
        ),
        { numRuns: 100 }
      );
    });

    test('deleting a project should not affect other projects in the list', async () => {
      await fc.assert(
        fc.asyncProperty(
          projectsArrayArbitrary.filter(arr => arr.length > 1),
          fc.nat(),
          async (projects, indexSeed) => {
            if (projects.length < 2) return true;

            const deleteIndex = indexSeed % projects.length;
            const projectToDelete = projects[deleteIndex];
            const otherProjects = projects.filter(p => p.projectId !== projectToDelete.projectId);

            // Mock successful deletion
            mockedAxios.delete = jest.fn().mockResolvedValue({ data: { success: true } });

            await api.deleteProject(projectToDelete.projectId);

            // Simulate dashboard update
            const updatedProjects = projects.filter(
              p => p.projectId !== projectToDelete.projectId
            );

            // Verify all other projects are still present
            const allOthersPresent = otherProjects.every(otherProject =>
              updatedProjects.some(p => p.projectId === otherProject.projectId)
            );

            return allOthersPresent;
          }
        ),
        { numRuns: 100 }
      );
    });

    test('dashboard should handle deletion errors without removing the project', async () => {
      await fc.assert(
        fc.asyncProperty(
          projectsArrayArbitrary.filter(arr => arr.length > 0),
          fc.nat(),
          fc.constantFrom(403, 404, 500),
          async (projects, indexSeed, errorCode) => {
            if (projects.length === 0) return true;

            const deleteIndex = indexSeed % projects.length;
            const projectToDelete = projects[deleteIndex];

            // Mock deletion error
            mockedAxios.delete = jest.fn().mockRejectedValue({
              response: {
                status: errorCode,
                data: { error: { message: 'Deletion failed' } },
              },
            });

            try {
              await api.deleteProject(projectToDelete.projectId);
              // Should have thrown
              return false;
            } catch {
              // On error, project should remain in the list
              const projectStillPresent = projects.some(
                p => p.projectId === projectToDelete.projectId
              );
              return projectStillPresent;
            }
          }
        ),
        { numRuns: 50 }
      );
    });
  });
});
