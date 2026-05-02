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

export const uploadImageToS3 = async (base64Image, fileName) => {
  try {
    const response = await api.post('/upload-image', {
      imageBase64: base64Image,
      fileName: fileName
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading image:', error);
    throw error;
  }
};

export const getValidationBacklog = async (status = 'pending_review', limit = 50) => {
  try {
    const response = await api.get('/validation-backlog', { params: { status, limit } });
    return response.data;
  } catch (error) {
    console.error('Error fetching validation backlog:', error);
    throw error;
  }
};

export const updateValidationReview = async (backlogId, { status, notes, reviewedBy }) => {
  try {
    const payload = { backlogId, status };
    if (notes?.trim()) payload.notes = notes.trim();
    if (reviewedBy) payload.reviewedBy = reviewedBy;
    const response = await api.put('/validation-backlog', payload);
    return response.data;
  } catch (error) {
    console.error('Error updating validation review:', error);
    throw error;
  }
};

export const getPermits = async (limit = 100) => {
  try {
    const response = await api.get('/permits', { params: { limit } });
    return response.data;
  } catch (error) {
    console.error('Error fetching permits:', error);
    throw error;
  }
};

export const createPermit = async ({ vehicleId, owner, expiryDate }) => {
  try {
    const response = await api.post('/permits', { vehicleId, owner, expiryDate });
    return response.data;
  } catch (error) {
    console.error('Error creating permit:', error);
    throw error;
  }
};

export const updatePermit = async (vehicleId, { status, owner, expiryDate }) => {
  try {
    const payload = { vehicleId };
    if (status) payload.status = status;
    if (owner) payload.owner = owner;
    if (expiryDate) payload.expiryDate = expiryDate;
    const response = await api.put('/permits', payload);
    return response.data;
  } catch (error) {
    console.error('Error updating permit:', error);
    throw error;
  }
};

export const getCitationsByPlate = async (plateText) => {
  try {
    const response = await api.get('/get-citations', {
      params: { plateText }
    });
    return response.data;
  } catch (error) {
    console.error('Error retrieving citations:', error);
    throw error;
  }
};

export const getAllCitations = async (status = null, limit = 50) => {
  try {
    const params = { limit };
    if (status) params.status = status;
    const response = await api.get('/admin-citations', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching all citations:', error);
    throw error;
  }
};

export const updateCitation = async (citationId, { status, notes, processedBy }) => {
  try {
    const payload = { citationId };
    if (status) payload.status = status;
    if (notes?.trim()) payload.notes = notes.trim();
    if (processedBy) payload.processedBy = processedBy;
    const response = await api.put('/admin-citations', payload);
    return response.data;
  } catch (error) {
    console.error('Error updating citation:', error);
    throw error;
  }
};

export default api;
