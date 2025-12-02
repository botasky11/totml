import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Play, Pause, Download, Code, BarChart3 } from 'lucide-react';
import { experimentAPI } from '@/services/api';
import { WebSocketService } from '@/services/websocket';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { WebSocketMessage } from '@/types';

export function ExperimentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'code' | 'metrics' | 'logs'>('overview');
  const [wsMessages, setWsMessages] = useState<WebSocketMessage[]>([]);

  const { data: experiment, isLoading, refetch } = useQuery({
    queryKey: ['experiment', id],
    queryFn: () => experimentAPI.get(id!),
    enabled: !!id,
    refetchInterval: (data) => data?.status === 'running' ? 2000 : false,
  });

  const { data: nodes } = useQuery({
    queryKey: ['experiment-nodes', id],
    queryFn: () => experimentAPI.getNodes(id!),
    enabled: !!id && experiment?.status === 'completed',
  });

  // WebSocket connection
  useEffect(() => {
    if (!id || experiment?.status !== 'running') return;

    const ws = new WebSocketService(id);
    ws.connect();

    const unsubscribe = ws.subscribe((message) => {
      setWsMessages((prev) => [...prev, message]);
      
      if (message.type === 'status_update' || message.type === 'complete') {
        refetch();
      }
    });

    return () => {
      unsubscribe();
      ws.disconnect();
    };
  }, [id, experiment?.status, refetch]);

  const handleRun = async () => {
    if (!id) return;
    await experimentAPI.run(id);
    refetch();
  };

  const handleDownload = () => {
    if (!experiment?.best_solution_code) return;
    
    const blob = new Blob([experiment.best_solution_code], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${experiment.name.replace(/\s+/g, '_')}_solution.py`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Prepare chart data
  const chartData = nodes
    ?.filter(node => !node.is_buggy && node.metric_value)
    .map((node, index) => ({
      step: node.step,
      metric: node.metric_value,
      index: index + 1,
    })) || [];

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (!experiment) {
    return (
      <div className="container mx-auto py-8 px-4">
        <p>实验未找到</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <Button
        variant="ghost"
        className="mb-6"
        onClick={() => navigate('/')}
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        返回仪表盘
      </Button>

      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">{experiment.name}</h1>
          <p className="text-gray-600 mt-2">{experiment.description}</p>
        </div>
        <div className="flex gap-2">
          {experiment.status === 'pending' && (
            <Button onClick={handleRun} className="gap-2">
              <Play className="w-4 h-4" />
              运行实验
            </Button>
          )}
          {experiment.best_solution_code && (
            <Button 
              onClick={handleDownload} 
              variant="secondary" 
              size="lg"
              className="gap-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 shadow-md hover:shadow-lg transition-all duration-200"
            >
              <Download className="w-5 h-5" />
              下载方案
            </Button>
          )}
        </div>
      </div>

      {/* Status Card */}
      {experiment.status === 'running' && (
        <Card className="mb-6 border-blue-200 bg-blue-50">
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-lg font-medium">运行中...</span>
                <span className="text-lg font-bold">
                  步骤 {experiment.current_step} / {experiment.num_steps}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-primary h-3 rounded-full transition-all duration-500"
                  style={{ width: `${experiment.progress * 100}%` }}
                />
              </div>
              <div className="text-sm text-gray-600">
                进度: {Math.round(experiment.progress * 100)}%
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { key: 'overview', label: '概览' },
            { key: 'code', label: '代码' },
            { key: 'metrics', label: '指标' },
            { key: 'logs', label: '日志' }
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${activeTab === tab.key
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'overview' && (
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>配置</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="text-sm font-medium text-gray-500">目标</span>
                  <p className="mt-1">{experiment.goal}</p>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">评估指标</span>
                  <p className="mt-1">{experiment.eval_metric}</p>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">模型</span>
                  <p className="mt-1">{experiment.model_name || 'gpt-4-turbo'}</p>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-500">步数</span>
                  <p className="mt-1">{experiment.num_steps}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>结果</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="text-sm font-medium text-gray-500">状态</span>
                  <p className="mt-1 capitalize font-medium">{
                    experiment.status === 'completed' ? '已完成' :
                    experiment.status === 'running' ? '运行中' :
                    experiment.status === 'failed' ? '失败' : '待运行'
                  }</p>
                </div>
                {experiment.best_metric_value && (
                  <div>
                    <span className="text-sm font-medium text-gray-500">最佳指标值</span>
                    <p className="mt-1 text-2xl font-bold text-primary">
                      {experiment.best_metric_value.toFixed(6)}
                    </p>
                  </div>
                )}
                {experiment.error_message && (
                  <div>
                    <span className="text-sm font-medium text-red-500">错误</span>
                    <p className="mt-1 text-sm text-red-600">{experiment.error_message}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'code' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="w-5 h-5" />
                最佳方案代码
              </CardTitle>
              <CardDescription>
                智能助手生成的最佳性能代码
              </CardDescription>
            </CardHeader>
            <CardContent>
              {experiment.best_solution_code ? (
                <SyntaxHighlighter
                  language="python"
                  style={vscDarkPlus}
                  customStyle={{
                    borderRadius: '0.5rem',
                    fontSize: '0.875rem',
                  }}
                  showLineNumbers
                >
                  {experiment.best_solution_code}
                </SyntaxHighlighter>
              ) : (
                <p className="text-gray-500 text-center py-8">
                  暂无方案代码
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === 'metrics' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                性能指标趋势
              </CardTitle>
              <CardDescription>
                不同迭代的性能指标变化
              </CardDescription>
            </CardHeader>
            <CardContent>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="step" label={{ value: '步骤', position: 'insideBottom', offset: -5 }} />
                    <YAxis label={{ value: '指标值', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="metric"
                      stroke="#8884d8"
                      strokeWidth={2}
                      dot={{ fill: '#8884d8', r: 4 }}
                      activeDot={{ r: 6 }}
                      name="指标"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-500 text-center py-8">
                  暂无指标数据
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === 'logs' && (
          <Card>
            <CardHeader>
              <CardTitle>实时日志</CardTitle>
              <CardDescription>
                实验执行的实时更新
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm max-h-96 overflow-y-auto">
                {wsMessages.length > 0 ? (
                  wsMessages.map((msg, index) => (
                    <div key={index} className="mb-2">
                      <span className="text-gray-500">[{new Date(msg.timestamp).toLocaleTimeString()}]</span>
                      <span className="ml-2">{JSON.stringify(msg.data, null, 2)}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500">暂无日志</p>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
