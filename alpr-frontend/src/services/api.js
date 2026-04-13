import axios from 'axios';

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const api = axios.create({
  baseURL: API_ENDPOINT,
  headers: {
    'Content-Type': 'application/json',
  }
});

/**
 * Get pre-signed URL for S3 upload
 */
export const getPresignedUrl = async () => {
  try {
    return {
      uploadUrl: 'https://s3.mock.amazonaws.com/upload',
      expiresIn: 3600
    };
  } catch (error) {
    console.error('Error getting pre-signed URL:', error);
    throw error;
  }
};

/**
 * Get permit status for a vehicle
 */
export const getPermitStatus = async (vehicleId) => {
  try {
    const mockData = {
      'ABC-1234': {
        vehicleId: 'ABC-1234',
        owner: 'John Doe',
        permitStatus: 'VALID',
        expiryDate: '2025-12-31'
      },
      'XYZ-5678': {
        vehicleId: 'XYZ-5678',
        owner: 'Jane Smith',
        permitStatus: 'EXPIRED',
        expiryDate: '2024-06-30'
      },
      'DEF-9012': {
        vehicleId: 'DEF-9012',
        owner: 'Bob Johnson',
        permitStatus: 'VALID',
        expiryDate: '2025-08-15'
      }
    };

    if (mockData[vehicleId]) {
      return mockData[vehicleId];
    } else {
      throw new Error('Vehicle not found');
    }
  } catch (error) {
    console.error('Error fetching permit:', error);
    throw error;
  }
};

/**
 * Get recent events
 */
export const getEvents = async (limit = 50) => {
  try {
    // For MVP, return mock events
    const now = Date.now();
    return [
      {
        timestamp: now - 5 * 60000,
        vehicleId: 'ABC-1234',
        plateText: 'ABC-1234',
        confidence: 0.98,
        permitStatus: 'VALID',
        eventType: 'ENTRY'
      },
      {
        timestamp: now - 15 * 60000,
        vehicleId: 'XYZ-5678',
        plateText: 'XYZ-5678',
        confidence: 0.95,
        permitStatus: 'EXPIRED',
        eventType: 'ENTRY'
      },
      {
        timestamp: now - 25 * 60000,
        vehicleId: 'DEF-9012',
        plateText: 'DEF-9012',
        confidence: 0.92,
        permitStatus: 'VALID',
        eventType: 'EXIT'
      },
      {
        timestamp: now - 35 * 60000,
        vehicleId: 'ABC-1234',
        plateText: 'ABC-1234',
        confidence: 0.97,
        permitStatus: 'VALID',
        eventType: 'EXIT'
      }
    ];
  } catch (error) {
    console.error('Error fetching events:', error);
    throw error;
  }
};

/**
 * Submit a plate recognition result
 */
export const submitPlateResult = async (result) => {
  try {
    console.log('Mock: Submitting result:', result);
    return { message: 'Result recorded' };
  } catch (error) {
    console.error('Error submitting result:', error);
    throw error;
  }
};

export default api;
