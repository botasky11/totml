import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { experimentAPI } from '@/services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FileText, RefreshCw, AlertCircle, CheckCircle, TrendingUp, BarChart2, Shield, Database } from 'lucide-react';
import type { FeatureAnalysisReport } from '@/types';

interface FeatureAnalysisReportProps {
  experimentId: string;
  experimentStatus: string;
}

export function FeatureAnalysisReportView({ experimentId, experimentStatus }: FeatureAnalysisReportProps) {
  const queryClient = useQueryClient();
  const [activeSection, setActiveSection] = useState<'overview' | 'data' | 'importance' | 'stability' | 'markdown'>('overview');

  // 获取分析报告
  const { data: report, isLoading, error } = useQuery({
    queryKey: ['feature-analysis', experimentId],
    queryFn: () => experimentAPI.getAnalysisReport(experimentId),
    enabled: !!experimentId && experimentStatus === 'completed',
    retry: false, // 如果报告不存在，不需要重试
  });

  // 生成/重新生成报告
  const generateMutation = useMutation({
    mutationFn: () => experimentAPI.generateAnalysisReport(experimentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feature-analysis', experimentId] });
    },
  });

  // 如果实验未完成
  if (experimentStatus !== 'completed') {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">
              实验完成后将自动生成特征分析报告
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // 加载中
  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-3 text-gray-500">加载分析报告...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // 报告不存在，提供生成按钮
  if (error || !report) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <AlertCircle className="w-12 h-12 text-yellow-400 mx-auto mb-3" />
            <p className="text-gray-600 mb-4">
              暂无特征分析报告
            </p>
            <Button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
              className="gap-2"
            >
              {generateMutation.isPending ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4" />
                  生成分析报告
                </>
              )}
            </Button>
            {generateMutation.isError && (
              <p className="text-red-500 mt-3 text-sm">
                生成失败: {(generateMutation.error as Error)?.message || '未知错误'}
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // 渲染报告内容
  return (
    <div className="space-y-6">
      {/* 顶部操作栏 */}
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          {[
            { key: 'overview', label: '概览', icon: BarChart2 },
            { key: 'data', label: '数据统计', icon: Database },
            { key: 'importance', label: '特征重要性', icon: TrendingUp },
            { key: 'stability', label: '稳定性分析', icon: Shield },
            { key: 'markdown', label: '完整报告', icon: FileText },
          ].map((tab) => (
            <Button
              key={tab.key}
              variant={activeSection === tab.key ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveSection(tab.key as any)}
              className="gap-1"
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </Button>
          ))}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="gap-1"
        >
          <RefreshCw className={`w-4 h-4 ${generateMutation.isPending ? 'animate-spin' : ''}`} />
          重新生成
        </Button>
      </div>

      {/* 错误提示 */}
      {report.error_message && (
        <Card className="border-yellow-300 bg-yellow-50">
          <CardContent className="pt-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-yellow-800">部分分析未完成</p>
                <p className="text-sm text-yellow-700 mt-1">{report.error_message}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 概览 */}
      {activeSection === 'overview' && (
        <OverviewSection report={report} />
      )}

      {/* 数据统计 */}
      {activeSection === 'data' && (
        <DataProfileSection report={report} />
      )}

      {/* 特征重要性 */}
      {activeSection === 'importance' && (
        <FeatureImportanceSection report={report} />
      )}

      {/* 稳定性分析 */}
      {activeSection === 'stability' && (
        <StabilitySection report={report} />
      )}

      {/* 完整 Markdown 报告 */}
      {activeSection === 'markdown' && (
        <MarkdownReportSection report={report} />
      )}
    </div>
  );
}

// 概览部分
function OverviewSection({ report }: { report: FeatureAnalysisReport }) {
  const config = report.analysis_config;
  const nodeStats = config?.node_statistics;

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      {/* 节点统计 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-500">节点统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">总节点数</span>
              <span className="font-semibold">{config?.total_nodes || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">有效节点</span>
              <span className="font-semibold text-green-600">{config?.good_nodes || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Buggy 节点</span>
              <span className="font-semibold text-red-600">{config?.buggy_nodes || 0}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 最佳指标 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-gray-500">最佳指标</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-bold text-primary">
            {config?.best_node_metric?.toFixed(4) || 'N/A'}
          </p>
        </CardContent>
      </Card>

      {/* 数据概况 */}
      {report.data_profile && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">数据概况</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">样本数</span>
                <span className="font-semibold">{report.data_profile.sample_count?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">特征数</span>
                <span className="font-semibold">{report.data_profile.feature_count}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 节点性能分布 */}
      {nodeStats && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">指标分布</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">均值</span>
                <span>{nodeStats.mean?.toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">标准差</span>
                <span>{nodeStats.std?.toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">范围</span>
                <span>{nodeStats.min?.toFixed(4)} ~ {nodeStats.max?.toFixed(4)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// 数据统计部分
function DataProfileSection({ report }: { report: FeatureAnalysisReport }) {
  const profile = report.data_profile;

  if (!profile) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-gray-500 text-center py-8">暂无数据统计信息</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* 基础信息 */}
      <Card>
        <CardHeader>
          <CardTitle>基础信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <span className="text-sm text-gray-500">数据文件</span>
              <p className="font-medium">{profile.file_name}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">样本数量</span>
              <p className="font-medium">{profile.sample_count?.toLocaleString()}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">特征数量</span>
              <p className="font-medium">{profile.feature_count}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">正负样本比例</span>
              <p className="font-medium">{profile.majority_minority_ratio}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据集分组统计 */}
      {profile.dataset_stats && profile.dataset_stats.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>数据集分组统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-4 font-medium">数据集</th>
                    <th className="text-right py-2 px-4 font-medium">样本数</th>
                    <th className="text-right py-2 px-4 font-medium">正样本数</th>
                    <th className="text-right py-2 px-4 font-medium">正样本率</th>
                    <th className="text-right py-2 px-4 font-medium">开始日期</th>
                    <th className="text-right py-2 px-4 font-medium">结束日期</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.dataset_stats.map((stat, index) => (
                    <tr key={index} className="border-b last:border-0">
                      <td className="py-2 px-4 font-medium">{stat.name}</td>
                      <td className="py-2 px-4 text-right">{stat.cnt?.toLocaleString()}</td>
                      <td className="py-2 px-4 text-right">{stat.blk_cnt?.toLocaleString()}</td>
                      <td className="py-2 px-4 text-right">{stat.blk_rate}</td>
                      <td className="py-2 px-4 text-right">{stat.dt_min}</td>
                      <td className="py-2 px-4 text-right">{stat.dt_max}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// 特征重要性部分
function FeatureImportanceSection({ report }: { report: FeatureAnalysisReport }) {
  const importance = report.feature_importance;

  if (!importance) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-gray-500 text-center py-8">暂无特征重要性分析</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* IV 值分析 */}
      {importance.iv_results && importance.iv_results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>特征 IV 值分析</CardTitle>
            <CardDescription>
              Information Value 衡量特征的预测能力
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-4 font-medium">排名</th>
                    <th className="text-left py-2 px-4 font-medium">特征名</th>
                    <th className="text-right py-2 px-4 font-medium">IV 值</th>
                    <th className="text-left py-2 px-4 font-medium">预测力评级</th>
                  </tr>
                </thead>
                <tbody>
                  {importance.iv_results.slice(0, 20).map((result, index) => (
                    <tr key={index} className="border-b last:border-0">
                      <td className="py-2 px-4">{index + 1}</td>
                      <td className="py-2 px-4 font-mono text-xs">{result.feature}</td>
                      <td className="py-2 px-4 text-right font-mono">{result.iv?.toFixed(6)}</td>
                      <td className="py-2 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          result.iv_strength === '强预测力' ? 'bg-green-100 text-green-800' :
                          result.iv_strength === '中等预测力' ? 'bg-blue-100 text-blue-800' :
                          result.iv_strength === '弱预测力' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {result.iv_strength}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 模型特征重要性 */}
      {importance.model_importance && importance.model_importance.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>模型特征重要性</CardTitle>
            <CardDescription>
              基于模型训练得到的特征重要性排序
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-4 font-medium">排名</th>
                    <th className="text-left py-2 px-4 font-medium">特征名</th>
                    <th className="text-right py-2 px-4 font-medium">重要性分数</th>
                    <th className="text-right py-2 px-4 font-medium">占比</th>
                    <th className="text-right py-2 px-4 font-medium">累计占比</th>
                  </tr>
                </thead>
                <tbody>
                  {importance.model_importance.slice(0, 20).map((result) => (
                    <tr key={result.rank} className="border-b last:border-0">
                      <td className="py-2 px-4">{result.rank}</td>
                      <td className="py-2 px-4 font-mono text-xs">{result.feature}</td>
                      <td className="py-2 px-4 text-right font-mono">{result.importance?.toFixed(4)}</td>
                      <td className="py-2 px-4 text-right">{result.importance_pct}</td>
                      <td className="py-2 px-4 text-right">{result.cumulative_pct}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// 稳定性分析部分
function StabilitySection({ report }: { report: FeatureAnalysisReport }) {
  const featureStability = report.feature_stability;
  const modelStability = report.model_stability;

  if (!featureStability && !modelStability) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-gray-500 text-center py-8">暂无稳定性分析数据（需要时间维度数据）</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* 特征稳定性 */}
      {featureStability && featureStability.feature_timelines && featureStability.feature_timelines.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>特征稳定性 (PSI)</CardTitle>
            <CardDescription>
              基准期: {featureStability.base_period}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* 不稳定特征警告 */}
            {featureStability.unstable_features && featureStability.unstable_features.length > 0 && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center gap-2 text-yellow-800">
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-medium">
                    {featureStability.unstable_features.length} 个特征不稳定 (PSI ≥ 0.25)
                  </span>
                </div>
                <p className="text-sm text-yellow-700 mt-1">
                  {featureStability.unstable_features.join(', ')}
                </p>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-4 font-medium">特征名</th>
                    <th className="text-right py-2 px-4 font-medium">最大 PSI</th>
                    <th className="text-right py-2 px-4 font-medium">平均 PSI</th>
                    <th className="text-left py-2 px-4 font-medium">稳定性</th>
                  </tr>
                </thead>
                <tbody>
                  {featureStability.feature_timelines.slice(0, 20).map((ft, index) => (
                    <tr key={index} className="border-b last:border-0">
                      <td className="py-2 px-4 font-mono text-xs">{ft.feature}</td>
                      <td className="py-2 px-4 text-right font-mono">{ft.max_psi?.toFixed(6)}</td>
                      <td className="py-2 px-4 text-right font-mono">{ft.avg_psi?.toFixed(6)}</td>
                      <td className="py-2 px-4">
                        {ft.is_stable ? (
                          <span className="inline-flex items-center gap-1 text-green-600">
                            <CheckCircle className="w-4 h-4" />
                            稳定
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-red-600">
                            <AlertCircle className="w-4 h-4" />
                            不稳定
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 模型稳定性 */}
      {modelStability && (
        <Card>
          <CardHeader>
            <CardTitle>模型分数稳定性</CardTitle>
            <CardDescription>
              分数列: {modelStability.score_column} | 基准期: {modelStability.base_period}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <span className="text-sm text-gray-500">整体 PSI</span>
                <p className="text-2xl font-bold">{modelStability.overall_psi?.toFixed(6)}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500">稳定性评级</span>
                <p className={`text-xl font-semibold ${
                  modelStability.is_stable ? 'text-green-600' : 'text-red-600'
                }`}>
                  {modelStability.stability_level}
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-500">状态</span>
                <p className="flex items-center gap-2 mt-1">
                  {modelStability.is_stable ? (
                    <>
                      <CheckCircle className="w-5 h-5 text-green-600" />
                      <span className="text-green-600 font-medium">稳定</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-5 h-5 text-red-600" />
                      <span className="text-red-600 font-medium">需关注</span>
                    </>
                  )}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Markdown 报告部分
function MarkdownReportSection({ report }: { report: FeatureAnalysisReport }) {
  if (!report.full_report_md) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-gray-500 text-center py-8">暂无完整报告</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>完整 Markdown 报告</CardTitle>
        <CardDescription>
          生成时间: {new Date(report.created_at).toLocaleString()}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono overflow-x-auto">
            {report.full_report_md}
          </pre>
        </div>
      </CardContent>
    </Card>
  );
}
