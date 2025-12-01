import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, Play, Trash2, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { experimentAPI } from '@/services/api';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import type { Experiment, ExperimentStatus } from '@/types';
import { format } from 'date-fns';

const getStatusIcon = (status: ExperimentStatus) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    case 'running':
      return <Play className="w-5 h-5 text-blue-500 animate-pulse" />;
    case 'failed':
      return <XCircle className="w-5 h-5 text-red-500" />;
    default:
      return <Clock className="w-5 h-5 text-gray-500" />;
  }
};

const getStatusColor = (status: ExperimentStatus) => {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800';
    case 'running':
      return 'bg-blue-100 text-blue-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

export function Dashboard() {
  const { data: experiments, isLoading, refetch } = useQuery({
    queryKey: ['experiments'],
    queryFn: () => experimentAPI.list(),
    refetchInterval: 5000, // Refetch every 5 seconds
  });

  const handleDelete = async (experimentId: string) => {
    if (window.confirm('Are you sure you want to delete this experiment?')) {
      await experimentAPI.delete(experimentId);
      refetch();
    }
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">AIDE ML Dashboard</h1>
          <p className="text-gray-600 mt-2">Enterprise Machine Learning Engineering Agent</p>
        </div>
        <Link to="/experiments/new">
          <Button size="lg" className="gap-2">
            <Plus className="w-5 h-5" />
            New Experiment
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {experiments?.map((experiment) => (
            <Card key={experiment.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <CardTitle className="text-xl mb-2">{experiment.name}</CardTitle>
                    <CardDescription className="line-clamp-2">
                      {experiment.description || experiment.goal}
                    </CardDescription>
                  </div>
                  {getStatusIcon(experiment.status as ExperimentStatus)}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">Status</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(experiment.status as ExperimentStatus)}`}>
                      {experiment.status}
                    </span>
                  </div>

                  {experiment.status === 'running' && (
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Progress</span>
                        <span className="font-medium">{Math.round(experiment.progress * 100)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all"
                          style={{ width: `${experiment.progress * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">
                        Step {experiment.current_step} / {experiment.num_steps}
                      </span>
                    </div>
                  )}

                  {experiment.best_metric_value && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">Best Metric</span>
                      <span className="text-sm font-medium">{experiment.best_metric_value.toFixed(4)}</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">Created</span>
                    <span className="text-sm">{format(new Date(experiment.created_at), 'MMM d, yyyy')}</span>
                  </div>

                  <div className="flex gap-2 pt-2">
                    <Link to={`/experiments/${experiment.id}`} className="flex-1">
                      <Button variant="outline" className="w-full">
                        View Details
                      </Button>
                    </Link>
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => handleDelete(experiment.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {experiments?.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center h-64 text-gray-500">
              <AlertCircle className="w-16 h-16 mb-4" />
              <p className="text-xl font-medium">No experiments yet</p>
              <p className="text-sm mt-2">Create your first experiment to get started</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
