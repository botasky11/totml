import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { ArrowLeft, Upload, Play } from 'lucide-react';
import { experimentAPI } from '@/services/api';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import type { ExperimentCreate } from '@/types';

export function NewExperiment() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<ExperimentCreate>({
    name: '',
    description: '',
    goal: '',
    eval_metric: '',
    num_steps: 20,
    model_name: 'gpt-4-turbo',
  });
  const [files, setFiles] = useState<File[]>([]);

  const createMutation = useMutation({
    mutationFn: async () => {
      // Create experiment
      const experiment = await experimentAPI.create(formData);
      
      // Upload files if any
      if (files.length > 0) {
        await experimentAPI.uploadFiles(experiment.id, files);
      }
      
      return experiment;
    },
    onSuccess: (experiment) => {
      navigate(`/experiments/${experiment.id}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-4xl">
      <Button
        variant="ghost"
        className="mb-6"
        onClick={() => navigate('/')}
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Dashboard
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-3xl">Create New Experiment</CardTitle>
          <CardDescription>
            Configure your machine learning experiment and let AIDE ML optimize your model
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                  Experiment Name <span className="text-red-500">*</span>
                </label>
                <input
                  id="name"
                  type="text"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="e.g., House Price Prediction"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  id="description"
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="Brief description of your experiment"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
            </div>

            {/* Goal and Metric */}
            <div className="space-y-4">
              <div>
                <label htmlFor="goal" className="block text-sm font-medium text-gray-700 mb-2">
                  Goal <span className="text-red-500">*</span>
                </label>
                <textarea
                  id="goal"
                  rows={3}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="e.g., Predict the sales price for each house based on the provided features"
                  value={formData.goal}
                  onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
                />
                <p className="text-sm text-gray-500 mt-1">
                  Describe what you want the model to achieve
                </p>
              </div>

              <div>
                <label htmlFor="eval_metric" className="block text-sm font-medium text-gray-700 mb-2">
                  Evaluation Metric <span className="text-red-500">*</span>
                </label>
                <input
                  id="eval_metric"
                  type="text"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="e.g., RMSE between log-prices, Accuracy, F1-score"
                  value={formData.eval_metric}
                  onChange={(e) => setFormData({ ...formData, eval_metric: e.target.value })}
                />
                <p className="text-sm text-gray-500 mt-1">
                  How should the model's performance be measured?
                </p>
              </div>
            </div>

            {/* Model Configuration */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="num_steps" className="block text-sm font-medium text-gray-700 mb-2">
                  Number of Steps
                </label>
                <input
                  id="num_steps"
                  type="number"
                  min="1"
                  max="100"
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  value={formData.num_steps}
                  onChange={(e) => setFormData({ ...formData, num_steps: parseInt(e.target.value) })}
                />
                <p className="text-sm text-gray-500 mt-1">
                  Number of improvement iterations (1-100)
                </p>
              </div>

              <div>
                <label htmlFor="model_name" className="block text-sm font-medium text-gray-700 mb-2">
                  LLM Model
                </label>
                <select
                  id="model_name"
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  value={formData.model_name}
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                >
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="gpt-4">GPT-4</option>
                  <option value="claude-4-sonnet">Claude 4 Sonnet</option>
                  <option value="gemini-pro">Gemini Pro</option>
                </select>
              </div>
            </div>

            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Upload Dataset Files
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <input
                  type="file"
                  multiple
                  accept=".csv,.txt,.json,.md"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer text-primary hover:text-primary/80 font-medium"
                >
                  Choose files
                </label>
                <p className="text-sm text-gray-500 mt-2">
                  CSV, TXT, JSON, or MD files
                </p>
                {files.length > 0 && (
                  <div className="mt-4 text-left">
                    <p className="text-sm font-medium text-gray-700 mb-2">Selected files:</p>
                    <ul className="text-sm text-gray-600 space-y-1">
                      {files.map((file, index) => (
                        <li key={index} className="flex items-center gap-2">
                          <span className="w-2 h-2 bg-primary rounded-full"></span>
                          {file.name} ({(file.size / 1024).toFixed(2)} KB)
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex gap-4">
              <Button
                type="submit"
                size="lg"
                className="flex-1"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5 mr-2" />
                    Create & Run Experiment
                  </>
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={() => navigate('/')}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
