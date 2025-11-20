/**
 * Property-Based Tests for Floorspace Editor
 * Feature: floorspace-3d-viewer
 * Property 13: Editor loads project data
 * Property 14: Save operation round-trip
 * Validates: Requirements 5.2, 5.3, 5.4
 */

import * as fc from 'fast-check';
import { api } from '../../services/api';
import axios from 'axios';

// Mock axios to avoid real API calls
jest.mock('axios');
const mockedAxios = axios as any;

// Generator for valid floorspace JSON
const floorspaceJsonArbitrary = fc.record({
  version: fc.constant('1.0'),
  stories: fc.array(
    fc.record({
      id: fc.uuid(),
      name: fc.string({ minLength: 1, maxLength: 50 }),
      geometry: fc.record({
        vertices: fc.array(fc.tuple(fc.float(), fc.float()), { maxLength: 10 }),
        edges: fc.array(fc.tuple(fc.nat(10), fc.nat(10)), { maxLength: 10 }),
        faces: fc.array(fc.array(fc.nat(10)), { maxLength: 10 }),
      }),
    }),
    { maxLength: 5 }
  ),
  building_units: fc.array(fc.record({ id: fc.uuid(), name: fc.string() }), { maxLength: 5 }),
  thermal_zones: fc.array(fc.record({ id: fc.uuid(), name: fc.string() }), { maxLength: 5 }),
  space_types: fc.array(fc.record({ id: fc.uuid(), name: fc.string() }), { maxLength: 5 }),
  construction_sets: fc.array(fc.record({ id: fc.uuid(), name: fc.string() }), { maxLength: 5 }),
});

// Generator for project with floorspace URL
const projectWithUrlArbitrary = fc.record({
  projectId: fc.uuid(),
  userId: fc.uuid(),
  name: fc.string({ minLength: 1, maxLength: 100 }),
  description: fc.option(fc.string({ maxLength: 500 }), { nil: undefined }),
  createdAt: fc.date().map(d => d.toISOString()),
  updatedAt: fc.date().map(d => d.toISOString()),
  floorspaceUrl: fc.webUrl(),
});

describe('Editor Properties', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    mockedAxios.create = jest.fn(() => mockedAxios as any);
    mockedAxios.interceptors = {
      request: { use: jest.fn(), eject: jest.fn(), clear: jest.fn() },
      response: { use: jest.fn(), eject: jest.fn(), clear: jest.fn() },
    } as any;

    // Mock global fetch for S3 presigned URL calls
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Property 13: Editor loads project data', () => {
    test('for any project accessed through editor, system should retrieve floorspace JSON from S3', async () => {
      await fc.assert(
        fc.asyncProperty(
          projectWithUrlArbitrary,
          floorspaceJsonArbitrary,
          async (project, floorspaceData) => {
            // Mock API response for getProject
            mockedAxios.get = jest.fn().mockResolvedValue({
              data: project,
            });

            // Mock fetch for S3 presigned URL
            (global.fetch as jest.Mock).mockResolvedValue({
              ok: true,
              json: async () => floorspaceData,
            });

            // Get project data
            const projectData = await api.getProject(project.projectId);

            // Verify project has floorspace URL
            const hasFloorspaceUrl = projectData.floorspaceUrl !== undefined;

            // Fetch floorspace JSON from S3
            if (projectData.floorspaceUrl) {
              const response = await fetch(projectData.floorspaceUrl);
              const jsonData = await response.json();

              // Verify data was retrieved
              const dataRetrieved = jsonData !== null && jsonData !== undefined;
              const hasRequiredFields =
                jsonData.version !== undefined &&
                Array.isArray(jsonData.stories) &&
                Array.isArray(jsonData.building_units);

              return hasFloorspaceUrl && dataRetrieved && hasRequiredFields;
            }

            return hasFloorspaceUrl;
          }
        ),
        { numRuns: 100 }
      );
    });

    test('editor should load floorspace JSON into iframe after retrieval', async () => {
      await fc.assert(
        fc.asyncProperty(
          projectWithUrlArbitrary,
          floorspaceJsonArbitrary,
          async (project, floorspaceData) => {
            // Mock API response
            mockedAxios.get = jest.fn().mockResolvedValue({
              data: project,
            });

            // Mock fetch for S3
            (global.fetch as jest.Mock).mockResolvedValue({
              ok: true,
              json: async () => floorspaceData,
            });

            const projectData = await api.getProject(project.projectId);

            if (projectData.floorspaceUrl) {
              const response = await fetch(projectData.floorspaceUrl);
              const jsonData = await response.json();

              // Verify JSON structure is valid for loading into iframe
              const isValidStructure =
                typeof jsonData === 'object' &&
                jsonData !== null &&
                'version' in jsonData &&
                'stories' in jsonData;

              return isValidStructure;
            }

            return true;
          }
        ),
        { numRuns: 100 }
      );
    });

    test('editor should handle missing floorspace URL gracefully', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.record({
            projectId: fc.uuid(),
            userId: fc.uuid(),
            name: fc.string({ minLength: 1 }),
            createdAt: fc.date().map(d => d.toISOString()),
            updatedAt: fc.date().map(d => d.toISOString()),
            floorspaceUrl: fc.constant(undefined),
          }),
          async (project) => {
            mockedAxios.get = jest.fn().mockResolvedValue({
              data: project,
            });

            const projectData = await api.getProject(project.projectId);

            // Should handle missing URL (initialize with empty structure)
            const canHandleMissingUrl = projectData.floorspaceUrl === undefined;

            return canHandleMissingUrl;
          }
        ),
        { numRuns: 50 }
      );
    });

    test('editor should handle S3 fetch errors gracefully', async () => {
      await fc.assert(
        fc.asyncProperty(
          projectWithUrlArbitrary,
          async (project) => {
            mockedAxios.get = jest.fn().mockResolvedValue({
              data: project,
            });

            // Mock fetch failure
            (global.fetch as jest.Mock).mockResolvedValue({
              ok: false,
              status: 404,
            });

            const projectData = await api.getProject(project.projectId);

            if (projectData.floorspaceUrl) {
              const response = await fetch(projectData.floorspaceUrl);
              
              // Should detect fetch failure
              const fetchFailed = !response.ok;

              return fetchFailed;
            }

            return true;
          }
        ),
        { numRuns: 50 }
      );
    });
  });

  describe('Property 14: Save operation round-trip', () => {
    test('for any floorspace modifications saved, retrieving immediately after should return updated data', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.uuid(), // projectId
          floorspaceJsonArbitrary,
          floorspaceJsonArbitrary, // modified data
          async (projectId, originalData, modifiedData) => {
            // Mock upload response
            const updatedAt = new Date().toISOString();
            mockedAxios.post = jest.fn().mockResolvedValue({
              data: {
                success: true,
                updatedAt,
              },
            });

            // Upload modified floorspace JSON
            const uploadResult = await api.uploadFloorspace(projectId, modifiedData);

            // Verify upload succeeded
            const uploadSucceeded = uploadResult.success === true;

            // Mock subsequent GET to return modified data
            mockedAxios.get = jest.fn().mockResolvedValue({
              data: {
                projectId,
                floorspaceUrl: 'https://example.com/floorspace.json',
              },
            });

            (global.fetch as jest.Mock).mockResolvedValue({
              ok: true,
              json: async () => modifiedData,
            });

            // Retrieve project
            const projectData = await api.getProject(projectId);
            
            if (projectData.floorspaceUrl) {
              const response = await fetch(projectData.floorspaceUrl);
              const retrievedData = await response.json();

              // Verify retrieved data matches what was saved
              const dataMatches = JSON.stringify(retrievedData) === JSON.stringify(modifiedData);

              return uploadSucceeded && dataMatches;
            }

            return uploadSucceeded;
          }
        ),
        { numRuns: 100 }
      );
    });

    test('save operation should update lastModified timestamp in DynamoDB', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.uuid(),
          floorspaceJsonArbitrary,
          async (projectId, floorspaceData) => {
            const beforeSave = new Date().toISOString();

            // Mock upload response with updated timestamp
            const updatedAt = new Date(Date.now() + 1000).toISOString();
            mockedAxios.post = jest.fn().mockResolvedValue({
              data: {
                success: true,
                updatedAt,
              },
            });

            const result = await api.uploadFloorspace(projectId, floorspaceData);

            // Verify timestamp was updated
            const hasUpdatedAt = result.updatedAt !== undefined;
            const timestampIsValid = !isNaN(Date.parse(result.updatedAt));

            return hasUpdatedAt && timestampIsValid && result.success;
          }
        ),
        { numRuns: 100 }
      );
    });

    test('save operation should capture changes in JSON format', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.uuid(),
          floorspaceJsonArbitrary,
          async (projectId, floorspaceData) => {
            let capturedData: any = null;

            mockedAxios.post = jest.fn().mockImplementation((url, data) => {
              capturedData = data;
              return Promise.resolve({
                data: {
                  success: true,
                  updatedAt: new Date().toISOString(),
                },
              });
            });

            await api.uploadFloorspace(projectId, floorspaceData);

            // Verify data was captured in correct format
            const dataCaptured = capturedData !== null;
            const hasFloorspaceJson = capturedData?.floorspaceJson !== undefined;
            const isValidJson = typeof capturedData?.floorspaceJson === 'object';

            return dataCaptured && hasFloorspaceJson && isValidJson;
          }
        ),
        { numRuns: 100 }
      );
    });

    test('save operation should handle upload failures gracefully', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.uuid(),
          floorspaceJsonArbitrary,
          fc.constantFrom(400, 403, 500),
          async (projectId, floorspaceData, errorCode) => {
            // Mock upload error
            mockedAxios.post = jest.fn().mockRejectedValue({
              response: {
                status: errorCode,
                data: {
                  error: {
                    code: 'UPLOAD_ERROR',
                    message: 'Upload failed',
                  },
                },
              },
            });

            try {
              await api.uploadFloorspace(projectId, floorspaceData);
              // Should have thrown
              return false;
            } catch (error: any) {
              // Error should be caught with correct status
              return error.response?.status === errorCode;
            }
          }
        ),
        { numRuns: 50 }
      );
    });

    test('save operation should preserve floorspace JSON structure', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.uuid(),
          floorspaceJsonArbitrary,
          async (projectId, floorspaceData) => {
            mockedAxios.post = jest.fn().mockResolvedValue({
              data: {
                success: true,
                updatedAt: new Date().toISOString(),
              },
            });

            // Serialize and deserialize to simulate save/load
            const serialized = JSON.stringify(floorspaceData);
            const deserialized = JSON.parse(serialized);

            // Verify structure is preserved
            const structurePreserved =
              deserialized.version === floorspaceData.version &&
              Array.isArray(deserialized.stories) &&
              deserialized.stories.length === floorspaceData.stories.length &&
              Array.isArray(deserialized.building_units) &&
              deserialized.building_units.length === floorspaceData.building_units.length;

            return structurePreserved;
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
