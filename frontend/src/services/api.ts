import axios from 'axios';
import type { Experiment, ExperimentCreate, ExperimentNode, FeatureAnalysisReport } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const experimentAPI = {
  // Create a new experiment
  create: async (data: ExperimentCreate): Promise<Experiment> => {
    const response = await api.post<Experiment>('/experiments/', data);
    return response.data;
  },

  // List all experiments
  list: async (skip = 0, limit = 100): Promise<Experiment[]> => {
    const response = await api.get<Experiment[]>('/experiments/', {
      params: { skip, limit },
    });
    return response.data;
  },

  // Get a specific experiment
  get: async (experimentId: string): Promise<Experiment> => {
    const response = await api.get<Experiment>(`/experiments/${experimentId}`);
    return response.data;
  },

  // Update an experiment
  update: async (experimentId: string, data: Partial<Experiment>): Promise<Experiment> => {
    const response = await api.patch<Experiment>(`/experiments/${experimentId}`, data);
    return response.data;
  },

  // Delete an experiment
  delete: async (experimentId: string): Promise<void> => {
    await api.delete(`/experiments/${experimentId}`);
  },

  // Upload files for an experiment
  uploadFiles: async (experimentId: string, files: File[]): Promise<{ uploaded_files: string[] }> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await api.post(`/experiments/${experimentId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Run an experiment
  run: async (experimentId: string): Promise<{ message: string; experiment_id: string }> => {
    const response = await api.post(`/experiments/${experimentId}/run`);
    return response.data;
  },

  // Get experiment nodes
  getNodes: async (experimentId: string): Promise<ExperimentNode[]> => {
    const response = await api.get<ExperimentNode[]>(`/experiments/${experimentId}/nodes`);
    return response.data;
  },

  // Get feature analysis report
  getAnalysisReport: async (experimentId: string): Promise<FeatureAnalysisReport> => {
    const response = await api.get<FeatureAnalysisReport>(`/experiments/${experimentId}/analysis`);
    return response.data;
  },

  // Generate feature analysis report
  generateAnalysisReport: async (experimentId: string): Promise<FeatureAnalysisReport> => {
    const response = await api.post<FeatureAnalysisReport>(`/experiments/${experimentId}/analysis`);
    return response.data;
  },
};

export default api;
