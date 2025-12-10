import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Play, Download, Code, BarChart3, Loader2 } from 'lucide-react';
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
  const [isStarting, setIsStarting] = useState(false);
  const wsRef = useRef<WebSocketService | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const isMountedRef = useRef<boolean>(false); // 防止React Strict Mode双重挂载
  
  // 实时进度状态 - 用于立即响应WebSocket消息，避免异步refetch导致的延迟
  const [realtimeProgress, setRealtimeProgress] = useState<{
    current_step: number;
    progress: number;
    status: string;
  } | null>(null);

  const { data: experiment, isLoading, refetch } = useQuery({
    queryKey: ['experiment', id],
    queryFn: () => experimentAPI.get(id!),
    enabled: !!id,
    // 轮询条件：运行中或待运行状态时持续轮询，确保能捕获到失败状态
    refetchInterval: (query) => {
      const status = query?.state?.data?.status;
      return (status === 'running' || status === 'pending') ? 2000 : false;
    },
  });

  const { data: nodes, refetch: refetchNodes } = useQuery({
    queryKey: ['experiment-nodes', id],
    queryFn: () => experimentAPI.getNodes(id!),
    enabled: !!id && (experiment?.status === 'completed' || experiment?.status === 'running'),
    // 在运行中时每2秒轮询一次以获取新节点
    refetchInterval: (query) => {
      const status = query?.state?.data ? experiment?.status : undefined;
      return status === 'running' ? 2000 : false;
    },
  });

  // WebSocket连接管理 - 只在ID变化时创建/销毁连接
  useEffect(() => {
    if (!id) {
      console.log('[EXP_DETAIL] ⏭️ No experiment ID');
      return;
    }

    // 防止React Strict Mode双重挂载导致重复连接
    if (isMountedRef.current) {
      console.log('[EXP_DETAIL] ⏭️ Component already mounted (React Strict Mode), skipping WebSocket creation');
      return;
    }

    // 防止重复创建连接
    if (wsRef.current) {
      console.log('[EXP_DETAIL] ⏭️ WebSocket already exists, skipping creation');
      return;
    }

    // 标记组件已挂载
    isMountedRef.current = true;
    console.log('[EXP_DETAIL] 🔌 Initializing WebSocket connection for experiment:', id);
    const ws = new WebSocketService(id);
    ws.connect();
    wsRef.current = ws;

    const unsubscribe = ws.subscribe((message) => {
      console.log('[EXP_DETAIL] 📨 Message received in component:', message);
      setWsMessages((prev) => {
        const updated = [...prev, message];
        console.log('[EXP_DETAIL] Updated wsMessages array, total messages:', updated.length);
        return updated;
      });

      // 处理各种消息类型：状态更新、完成、错误
      if (message.type === 'status_update') {
        console.log('[EXP_DETAIL] 🔄 Status update received');
        
        // 立即更新实时进度，避免refetch()延迟
        const data = message.data as any;
        if (data) {
          console.log('[EXP_DETAIL] ⚡ Immediate progress update:', {
            step: data.step,
            progress: data.progress,
            status: data.status
          });
          setRealtimeProgress({
            current_step: data.step || 0,
            progress: data.progress || 0,
            status: data.status || 'running'
          });
        }
        
        // 后台同步数据
        refetch();
      } else if (message.type === 'complete' || message.type === 'error') {
        console.log('[EXP_DETAIL] 🏁 Experiment finished, message type:', message.type);
        
        // 清除实时进度，使用服务器数据
        setRealtimeProgress(null);
        
        // 刷新数据
        refetch();
        refetchNodes();
      }
    });

    unsubscribeRef.current = unsubscribe;
    console.log('[EXP_DETAIL] ✅ WebSocket subscription created for experiment:', id);

    // Cleanup：只在组件真正卸载或ID变化时执行
    return () => {
      // 在开发环境的Strict Mode下，这个cleanup会被调用两次
      // 但由于isMountedRef的保护，第二次挂载时不会重新创建连接
      console.log('[EXP_DETAIL] 🧹 Cleanup function called for experiment:', id);
      
      // 只在组件真正卸载时才断开连接（ID变化或离开页面）
      if (wsRef.current) {
        console.log('[EXP_DETAIL] 🔌 Disconnecting WebSocket');
        if (unsubscribeRef.current) {
          unsubscribeRef.current();
          unsubscribeRef.current = null;
        }
        wsRef.current.disconnect();
        wsRef.current = null;
      }
      
      // 重置挂载标志（为下次挂载准备）
      isMountedRef.current = false;
    };
  }, [id]); // 只依赖ID，确保连接稳定

  // 根据实验状态自动断开WebSocket (实验完成后)
  useEffect(() => {
    const status = experiment?.status;
    
    // 只在实验完成或失败且有活跃连接时断开
    if ((status === 'completed' || status === 'failed') && wsRef.current) {
      console.log('[EXP_DETAIL] 🏁 Experiment finished with status:', status);
      console.log('[EXP_DETAIL] 🔌 Disconnecting WebSocket');
      
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
    }
  }, [experiment?.status]); // 监听状态变化，仅用于断开连接

  const handleRun = async () => {
    if (!id || isStarting) return;
    
    setIsStarting(true);
    // 清除之前的实时进度
    setRealtimeProgress(null);
    console.log('[EXP_DETAIL] 🚀 Starting experiment:', id);
    
    try {
      const result = await experimentAPI.run(id);
      console.log('[EXP_DETAIL] ✅ Experiment run API call successful:', result);
      // 立即刷新以获取最新状态
      await refetch();
      console.log('[EXP_DETAIL] Refetch completed after run');
    } catch (error) {
      console.error('[EXP_DETAIL] ❌ Failed to start experiment:', error);
      // 如果启动失败，允许重试
      setIsStarting(false);
      // 即使出错也刷新，以获取最新的错误状态
      await refetch();
    }
  };

  // 合并实时进度和服务器数据，优先使用实时数据
  const displayProgress = realtimeProgress || {
    current_step: experiment?.current_step || 0,
    progress: experiment?.progress || 0,
    status: experiment?.status || 'pending'
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

  // Prepare chart data - 包括所有节点（即使是buggy的），便于调试
  // 如果有非buggy节点，优先显示；否则显示所有节点
  const goodChartData = nodes
    ?.filter(node => !node.is_buggy && node.metric_value != null)
    .map((node, index) => ({
      step: node.step,
      metric: node.metric_value,
      index: index + 1,
      isBuggy: false,
    })) || [];
    
  const allChartData = nodes
    ?.map((node, index) => ({
      step: node.step,
      metric: node.metric_value,
      index: index + 1,
      isBuggy: node.is_buggy,
    })) || [];
  
  // 如果有非buggy节点，使用好的数据；否则使用所有数据
  const chartData = goodChartData.length > 0 ? goodChartData : allChartData;

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
            <Button 
              onClick={handleRun} 
              disabled={isStarting}
              className="gap-2"
            >
              <Play className="w-4 h-4" />
              {isStarting ? '启动中...' : '运行实验'}
            </Button>
          )}
          {experiment.best_solution_code && (
            <Button 
              onClick={handleDownload} 
              variant="secondary" 
              size="lg"
              className="gap-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 shadow-md hover:shadow-lg transition-all duration-200 flex-row items-center whitespace-nowrap"
            >
              <Download className="w-5 h-5" />
              <span>下载方案</span>
            </Button>
          )}
        </div>
      </div>

      {/* Status Card - 运行中 */}
      {experiment.status === 'running' && (
        <Card className="mb-6 border-blue-300 bg-gradient-to-r from-blue-50 to-blue-100 shadow-lg relative overflow-hidden">
          {/* 动态背景效果 */}
          <div className="absolute inset-0 bg-gradient-to-r from-blue-400/10 via-transparent to-blue-400/10 animate-pulse"></div>
          
          {/* 移动的光效 */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute top-0 -left-full h-full w-1/2 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
          </div>
          
          <CardContent className="pt-6 relative z-10">
            <div className="space-y-4">
              {/* 标题行 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                  <span className="text-lg font-semibold text-blue-900 flex items-center gap-1">
                    运行中
                    <span className="inline-flex gap-0.5">
                      <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
                      <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
                      <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
                    </span>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-blue-700 font-medium">步骤</span>
                  <span className="text-2xl font-bold text-blue-900 tabular-nums">
                    {displayProgress.current_step}
                  </span>
                  <span className="text-lg text-blue-600">/</span>
                  <span className="text-xl font-semibold text-blue-700 tabular-nums">
                    {experiment.num_steps}
                  </span>
                </div>
              </div>
              
              {/* 进度条 */}
              <div className="space-y-2">
                <div className="w-full bg-blue-200/50 rounded-full h-4 shadow-inner overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-blue-500 via-blue-600 to-blue-500 h-4 rounded-full transition-all duration-700 ease-out relative overflow-hidden"
                    style={{ width: `${displayProgress.progress * 100}%` }}
                  >
                    {/* 进度条内的光效 */}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer-fast"></div>
                  </div>
                </div>
                
                {/* 进度百分比 */}
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-blue-700">
                    进度: <span className="text-base font-bold text-blue-900 tabular-nums">{Math.round(displayProgress.progress * 100)}%</span>
                  </span>
                  <span className="text-xs text-blue-600 animate-pulse">
                    正在处理...
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
          
          {/* 底部装饰线 */}
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-400 via-blue-500 to-blue-400 animate-pulse"></div>
        </Card>
      )}

      {/* Failed Status Card */}
      {experiment.status === 'failed' && (
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0">
                  <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-red-800">实验运行失败</h3>
                  {experiment.error_message && (
                    <div className="mt-2 text-sm text-red-700 bg-white rounded p-3 border border-red-200">
                      <p className="font-medium mb-1">错误信息：</p>
                      <p className="whitespace-pre-wrap break-words">{experiment.error_message}</p>
                    </div>
                  )}
                </div>
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
          <div className="space-y-4">
            {/* 最佳方案代码 */}
            {experiment.best_solution_code && (
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
                </CardContent>
              </Card>
            )}
            
            {/* 所有迭代的代码 */}
            {nodes && nodes.length > 0 ? (
              nodes.map((node, index) => (
                <Card key={node.id} className={node.is_buggy ? 'border-red-300' : 'border-green-300'}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Code className="w-4 h-4" />
                      步骤 {node.step} {node.is_buggy && <span className="text-red-500 text-sm">(包含错误)</span>}
                    </CardTitle>
                    {node.plan && (
                      <CardDescription className="text-sm">
                        <strong>计划:</strong> {node.plan}
                      </CardDescription>
                    )}
                    {node.metric_value != null && (
                      <CardDescription className="text-sm">
                        <strong>指标值:</strong> {node.metric_value}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                    <SyntaxHighlighter
                      language="python"
                      style={vscDarkPlus}
                      customStyle={{
                        borderRadius: '0.5rem',
                        fontSize: '0.75rem',
                        maxHeight: '400px',
                      }}
                      showLineNumbers
                    >
                      {node.code}
                    </SyntaxHighlighter>
                    
                    {/* 显示终端输出（如果有错误）*/}
                    {node.term_out && node.is_buggy && (
                      <div className="mt-4">
                        <h4 className="text-sm font-semibold text-red-600 mb-2">终端输出:</h4>
                        <pre className="bg-red-50 border border-red-200 rounded p-3 text-xs text-red-900 overflow-x-auto">
                          {node.term_out}
                        </pre>
                      </div>
                    )}
                    
                    {/* 显示分析（如果有）*/}
                    {node.analysis && (
                      <div className="mt-4">
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">分析:</h4>
                        <p className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded p-3">
                          {node.analysis}
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))
            ) : (
              <Card>
                <CardContent className="pt-6">
                  <p className="text-gray-500 text-center py-8">
                    暂无代码数据
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
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
