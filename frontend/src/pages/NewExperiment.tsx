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
    onError: (error) => {
      console.error('创建实验失败:', error);
      alert('创建实验失败，请查看控制台了解详情。');
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
        返回仪表盘
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-3xl">创建新实验</CardTitle>
          <CardDescription>
            配置您的机器学习实验，让智能助手优化您的模型
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                  实验名称 <span className="text-red-500">*</span>
                </label>
                <input
                  id="name"
                  type="text"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="例如：房价预测"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                  描述
                </label>
                <textarea
                  id="description"
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="简要描述您的实验"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
            </div>

            {/* Goal and Metric */}
            <div className="space-y-4">
              <div>
                <label htmlFor="goal" className="block text-sm font-medium text-gray-700 mb-2">
                  目标 <span className="text-red-500">*</span>
                </label>
                <textarea
                  id="goal"
                  rows={3}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="例如：基于提供的特征预测每栋房子的销售价格"
                  value={formData.goal}
                  onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
                />
                <p className="text-sm text-gray-500 mt-1">
                  描述您希望模型实现的目标
                </p>
              </div>

              <div>
                <label htmlFor="eval_metric" className="block text-sm font-medium text-gray-700 mb-2">
                  评估指标 <span className="text-red-500">*</span>
                </label>
                <input
                  id="eval_metric"
                  type="text"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="例如：对数价格之间的RMSE、准确率、F1分数"
                  value={formData.eval_metric}
                  onChange={(e) => setFormData({ ...formData, eval_metric: e.target.value })}
                />
                <p className="text-sm text-gray-500 mt-1">
                  如何衡量模型的性能？
                </p>
              </div>
            </div>

            {/* Model Configuration */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="num_steps" className="block text-sm font-medium text-gray-700 mb-2">
                  迭代步数
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
                  改进迭代次数 (1-100)
                </p>
              </div>

              <div>
                <label htmlFor="model_name" className="block text-sm font-medium text-gray-700 mb-2">
                  LLM 模型
                </label>
                <select
                  id="model_name"
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
                  value={formData.model_name}
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                >
                  <option value="qwen-max-latest">Qwen Max Latest</option>
                  <option value="deepseek-v3.2">DeepSeek V3.2</option>
                  <option value="qwen3-32b">Qwen 3 32B</option>
                  <option value="gpt-5.2">GPT-5.2</option>
                  <option value="claude-sonnet-4-5-20250929">Claude 4.5 Sonnet</option>
                  <option value="gemini-3-pro-preview">Gemini 3 Pro Preview</option>
                </select>
              </div>
            </div>

            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                上传数据集文件
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
                  选择文件
                </label>
                <p className="text-sm text-gray-500 mt-2">
                  支持 CSV、TXT、JSON 或 MD 文件
                </p>
                {files.length > 0 && (
                  <div className="mt-4 text-left">
                    <p className="text-sm font-medium text-gray-700 mb-2">已选择文件：</p>
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
                    创建中...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5 mr-2" />
                    创建并运行实验
                  </>
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={() => navigate('/')}
              >
                取消
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
