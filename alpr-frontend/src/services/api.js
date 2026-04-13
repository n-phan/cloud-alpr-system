import axios from 'axios';

// Get API endpoint from environment
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || 'https://o5h6jttjtc.execute-api.us-west-2.amazonaws.com/prod';

// Create axios instance
const api = axios.create({
  baseURL: API_ENDPOINT,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const getPresignedUrl = async () => {
  try {
    const response = await api.post('/presigned-url');
    return response.data;
  } catch (error) {
    console.error('Error getting presigned URL:', error);
    throw error;
  }
};

export const getPermitStatus = async (vehicleId) => {
  try {
    const response = await api.get('/check-permit', {
      params: { vehicleId }
    });
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      throw new Error(`Vehicle ${vehicleId} not found in system`);
    }
    console.error('Error checking permit:', error);
    throw error;
  }
};

export const getEvents = async (limit = 50) => {
  try {
    const response = await api.get('/get-events', {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    console.error('Error retrieving events:', error);
    throw error;
  }
};

export const submitPlateResult = async (result) => {
  try {
    const response = await api.post('/submit-plate', {
      vehicleId: result.vehicleId,
      plateText: result.plateText,
      confidence: result.confidence,
      permitStatus: result.permitStatus,
      eventType: result.eventType,
      imageUrl: result.imageUrl || null
    });
    return response.data;
  } catch (error) {
    console.error('Error submitting plate result:', error);
    throw error;
  }
};

export default api;
