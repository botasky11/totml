import { useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
  MarkerType,
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { ExperimentNode } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { X, ChevronDown, ChevronRight, Target, AlertCircle, CheckCircle, Star, Zap } from 'lucide-react';

// 节点数据类型 - 添加 index signature 以满足 Record<string, unknown> 约束
interface IterationNodeData extends Record<string, unknown> {
  label: string;
  step: number;
  metricValue?: number;
  isBuggy: boolean;
  isBestPath: boolean;
  isBest: boolean;
  plan?: string;
  code: string;
  termOut?: string;
  analysis?: string;
  isCollapsed: boolean;
  hasChildren: boolean;
  parentId?: string;
  onToggleCollapse: (nodeId: string) => void;
  onNodeClick: (node: ExperimentNode) => void;
  originalNode: ExperimentNode;
}

// 自定义节点类型
type IterationFlowNode = Node<IterationNodeData, 'iterationNode'>;

// 自定义节点组件 Props
interface IterationNodeProps {
  id: string;
  data: IterationNodeData;
}

// 自定义节点组件
const IterationNode = ({ data, id }: IterationNodeProps) => {
  const [isHovered, setIsHovered] = useState(false);
  
  // 根据状态确定节点样式
  const getNodeStyles = () => {
    if (data.isBest) {
      return {
        background: 'linear-gradient(135deg, #fef3c7 0%, #fcd34d 100%)',
        border: '3px solid #f59e0b',
        boxShadow: '0 0 20px rgba(245, 158, 11, 0.5)',
      };
    }
    if (data.isBestPath) {
      return {
        background: 'linear-gradient(135deg, #d1fae5 0%, #6ee7b7 100%)',
        border: '2px solid #10b981',
        boxShadow: '0 0 10px rgba(16, 185, 129, 0.3)',
      };
    }
    if (data.isBuggy) {
      return {
        background: 'linear-gradient(135deg, #fee2e2 0%, #fca5a5 100%)',
        border: '2px solid #ef4444',
        boxShadow: 'none',
      };
    }
    return {
      background: 'linear-gradient(135deg, #f0f9ff 0%, #bae6fd 100%)',
      border: '2px solid #0ea5e9',
      boxShadow: 'none',
    };
  };

  const nodeStyles = getNodeStyles();

  const handleClick = () => {
    data.onNodeClick(data.originalNode);
  };

  const handleCollapseToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    data.onToggleCollapse(id);
  };

  return (
    <div
      className="relative cursor-pointer transition-all duration-200"
      style={{
        ...nodeStyles,
        borderRadius: '12px',
        padding: '12px 16px',
        minWidth: '180px',
        maxWidth: '220px',
        transform: isHovered ? 'scale(1.05)' : 'scale(1)',
        zIndex: isHovered ? 10 : 1,
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleClick}
    >
      {/* 输入连接点 */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: '#6b7280',
          width: '10px',
          height: '10px',
          border: '2px solid #fff',
        }}
      />
      
      {/* 节点内容 */}
      <div className="flex flex-col gap-1">
        {/* 标题行 */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1">
            {data.isBest && <Star className="w-4 h-4 text-amber-600" fill="currentColor" />}
            {data.isBuggy ? (
              <AlertCircle className="w-4 h-4 text-red-600" />
            ) : (
              <CheckCircle className="w-4 h-4 text-green-600" />
            )}
            <span className="font-bold text-gray-800">Step {data.step}</span>
          </div>
          
          {/* 折叠按钮 */}
          {data.hasChildren && (
            <button
              onClick={handleCollapseToggle}
              className="p-1 rounded hover:bg-gray-200 transition-colors"
            >
              {data.isCollapsed ? (
                <ChevronRight className="w-4 h-4 text-gray-600" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-600" />
              )}
            </button>
          )}
        </div>
        
        {/* 指标值 */}
        {data.metricValue !== null && data.metricValue !== undefined && (
          <div className="flex items-center gap-1">
            <Target className="w-3 h-3 text-gray-500" />
            <span className="text-sm font-semibold text-gray-700">
              {data.metricValue.toFixed(4)}
            </span>
          </div>
        )}
        
        {/* 状态标签 */}
        <div className="flex gap-1 mt-1">
          {data.isBest && (
            <span className="px-2 py-0.5 bg-amber-500 text-white text-xs rounded-full">
              最佳
            </span>
          )}
          {data.isBestPath && !data.isBest && (
            <span className="px-2 py-0.5 bg-green-500 text-white text-xs rounded-full">
              最优路径
            </span>
          )}
          {data.isBuggy && (
            <span className="px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
              错误
            </span>
          )}
        </div>
      </div>
      
      {/* Hover 详情提示 */}
      {isHovered && (
        <div
          className="absolute left-full top-0 ml-2 z-50 bg-white rounded-lg shadow-xl border border-gray-200 p-3 min-w-[250px]"
          style={{ pointerEvents: 'none' }}
        >
          <div className="text-sm space-y-2">
            <div className="font-bold text-gray-800 border-b pb-1">
              Step {data.step} 详情
            </div>
            
            {data.metricValue !== null && data.metricValue !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">Score:</span>
                <span className="font-semibold text-blue-600">{data.metricValue.toFixed(6)}</span>
              </div>
            )}
            
            <div className="flex justify-between">
              <span className="text-gray-500">状态:</span>
              <span className={data.isBuggy ? 'text-red-600' : 'text-green-600'}>
                {data.isBuggy ? '执行错误' : '执行成功'}
              </span>
            </div>
            
            {data.plan && (
              <div>
                <span className="text-gray-500">计划:</span>
                <p className="text-xs text-gray-700 mt-1 line-clamp-3">{data.plan}</p>
              </div>
            )}
            
            <div className="text-xs text-gray-400 mt-2 pt-1 border-t">
              点击查看完整详情
            </div>
          </div>
        </div>
      )}
      
      {/* 输出连接点 */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: '#6b7280',
          width: '10px',
          height: '10px',
          border: '2px solid #fff',
        }}
      />
    </div>
  );
};

// 节点详情面板
interface NodeDetailPanelProps {
  node: ExperimentNode | null;
  onClose: () => void;
}

const NodeDetailPanel = ({ node, onClose }: NodeDetailPanelProps) => {
  if (!node) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b bg-gray-50">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${node.is_buggy ? 'bg-red-100' : 'bg-green-100'}`}>
              {node.is_buggy ? (
                <AlertCircle className="w-5 h-5 text-red-600" />
              ) : (
                <CheckCircle className="w-5 h-5 text-green-600" />
              )}
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">步骤 {node.step} 详情</h2>
              <p className="text-sm text-gray-500">
                {node.is_buggy ? '执行错误' : '执行成功'}
                {node.metric_value !== null && node.metric_value !== undefined && (
                  <span className="ml-2">• 指标值: {node.metric_value.toFixed(6)}</span>
                )}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>
        
        <div className="p-4 overflow-y-auto max-h-[calc(90vh-100px)] space-y-4">
          {/* 计划 */}
          {node.plan && (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Zap className="w-4 h-4 text-blue-500" />
                  执行计划
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{node.plan}</p>
              </CardContent>
            </Card>
          )}
          
          {/* 代码 */}
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-base">代码</CardTitle>
            </CardHeader>
            <CardContent>
              <SyntaxHighlighter
                language="python"
                style={vscDarkPlus}
                customStyle={{
                  borderRadius: '0.5rem',
                  fontSize: '0.75rem',
                  maxHeight: '300px',
                }}
                showLineNumbers
              >
                {node.code}
              </SyntaxHighlighter>
            </CardContent>
          </Card>
          
          {/* 终端输出 */}
          {node.term_out && (
            <Card className={node.is_buggy ? 'border-red-200' : ''}>
              <CardHeader className="py-3">
                <CardTitle className="text-base flex items-center gap-2">
                  {node.is_buggy && <AlertCircle className="w-4 h-4 text-red-500" />}
                  终端输出
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className={`text-xs p-3 rounded-lg overflow-x-auto ${
                  node.is_buggy 
                    ? 'bg-red-50 text-red-900 border border-red-200' 
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {node.term_out}
                </pre>
              </CardContent>
            </Card>
          )}
          
          {/* 分析 */}
          {node.analysis && (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">分析</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{node.analysis}</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

// 自动布局算法 - 树形布局 (左到右)
const calculateTreeLayout = (
  experimentNodes: ExperimentNode[],
  collapsedNodes: Set<string>
): { nodes: IterationFlowNode[]; edges: Edge[] } => {
  if (!experimentNodes || experimentNodes.length === 0) {
    return { nodes: [], edges: [] };
  }

  const HORIZONTAL_SPACING = 280;
  const VERTICAL_SPACING = 120;

  // 构建父子关系映射
  const nodeMap = new Map<string, ExperimentNode>();
  const childrenMap = new Map<string, string[]>();
  
  experimentNodes.forEach(node => {
    nodeMap.set(node.id, node);
    if (node.parent_id) {
      const children = childrenMap.get(node.parent_id) || [];
      children.push(node.id);
      childrenMap.set(node.parent_id, children);
    }
  });

  // 找到根节点 (没有parent_id的节点)
  const rootNodes = experimentNodes.filter(n => !n.parent_id);
  
  // 找到最佳节点
  const bestNode = experimentNodes.reduce((best, node) => {
    if (node.is_buggy) return best;
    if (!best) return node;
    if (node.metric_value !== null && node.metric_value !== undefined) {
      if (best.metric_value === null || best.metric_value === undefined) return node;
      // 假设指标值越高越好
      return node.metric_value > best.metric_value ? node : best;
    }
    return best;
  }, null as ExperimentNode | null);

  // 计算最优路径 (从最佳节点回溯到根节点)
  const bestPath = new Set<string>();
  if (bestNode) {
    let currentId: string | undefined = bestNode.id;
    while (currentId) {
      bestPath.add(currentId);
      const current = nodeMap.get(currentId);
      currentId = current?.parent_id;
    }
  }

  // 检查节点是否应该隐藏 (其祖先节点被折叠)
  const isNodeHidden = (nodeId: string): boolean => {
    const node = nodeMap.get(nodeId);
    if (!node || !node.parent_id) return false;
    if (collapsedNodes.has(node.parent_id)) return true;
    return isNodeHidden(node.parent_id);
  };

  // 计算每个节点的深度
  const depthMap = new Map<string, number>();
  const calculateDepth = (nodeId: string, depth: number) => {
    depthMap.set(nodeId, depth);
    const children = childrenMap.get(nodeId) || [];
    children.forEach(childId => calculateDepth(childId, depth + 1));
  };
  rootNodes.forEach(root => calculateDepth(root.id, 0));

  // 计算每层的节点数量，用于垂直居中
  const depthCountMap = new Map<number, number>();
  const depthIndexMap = new Map<string, number>();
  
  experimentNodes.forEach(node => {
    if (isNodeHidden(node.id)) return;
    const depth = depthMap.get(node.id) || 0;
    const currentCount = depthCountMap.get(depth) || 0;
    depthIndexMap.set(node.id, currentCount);
    depthCountMap.set(depth, currentCount + 1);
  });

  // 转换为 ReactFlow 节点和边
  const flowNodes: IterationFlowNode[] = [];
  const flowEdges: Edge[] = [];

  experimentNodes.forEach(node => {
    if (isNodeHidden(node.id)) return;

    const depth = depthMap.get(node.id) || 0;
    const indexInDepth = depthIndexMap.get(node.id) || 0;
    const totalInDepth = depthCountMap.get(depth) || 1;
    
    // 计算位置
    const x = depth * HORIZONTAL_SPACING;
    const totalHeight = totalInDepth * VERTICAL_SPACING;
    const startY = -totalHeight / 2;
    const y = startY + indexInDepth * VERTICAL_SPACING;

    const hasChildren = (childrenMap.get(node.id) || []).length > 0;
    const isBest = bestNode?.id === node.id;
    const isBestPath = bestPath.has(node.id);

    flowNodes.push({
      id: node.id,
      type: 'iterationNode',
      position: { x, y },
      data: {
        label: `Step ${node.step}`,
        step: node.step,
        metricValue: node.metric_value ?? undefined,
        isBuggy: node.is_buggy,
        isBestPath,
        isBest,
        plan: node.plan,
        code: node.code,
        termOut: node.term_out,
        analysis: node.analysis,
        isCollapsed: collapsedNodes.has(node.id),
        hasChildren,
        parentId: node.parent_id,
        onToggleCollapse: () => {},
        onNodeClick: () => {},
        originalNode: node,
      },
    });

    // 创建边
    if (node.parent_id && !isNodeHidden(node.id)) {
      const isBestEdge = isBestPath && bestPath.has(node.parent_id);
      flowEdges.push({
        id: `edge-${node.parent_id}-${node.id}`,
        source: node.parent_id,
        target: node.id,
        type: 'smoothstep',
        animated: isBestEdge,
        style: {
          stroke: isBestEdge ? '#10b981' : node.is_buggy ? '#ef4444' : '#6b7280',
          strokeWidth: isBestEdge ? 3 : 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isBestEdge ? '#10b981' : node.is_buggy ? '#ef4444' : '#6b7280',
        },
      });
    }
  });

  return { nodes: flowNodes, edges: flowEdges };
};

// 自定义节点类型
const nodeTypes = {
  iterationNode: IterationNode,
};

// 主图组件内容
interface IterationTreeGraphContentProps {
  experimentNodes: ExperimentNode[];
  bestMetricValue?: number;
}

const IterationTreeGraphContent = ({ experimentNodes, bestMetricValue }: IterationTreeGraphContentProps) => {
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<ExperimentNode | null>(null);
  const [highlightBestPath, setHighlightBestPath] = useState(true);
  const { fitView } = useReactFlow();

  // 计算布局
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => calculateTreeLayout(experimentNodes, collapsedNodes),
    [experimentNodes, collapsedNodes]
  );

  // 更新节点回调函数
  const nodesWithCallbacks = useMemo(() => {
    return initialNodes.map(node => ({
      ...node,
      data: {
        ...node.data,
        onToggleCollapse: (nodeId: string) => {
          setCollapsedNodes(prev => {
            const next = new Set(prev);
            if (next.has(nodeId)) {
              next.delete(nodeId);
            } else {
              next.add(nodeId);
            }
            return next;
          });
        },
        onNodeClick: (originalNode: ExperimentNode) => {
          setSelectedNode(originalNode);
        },
        isBestPath: highlightBestPath ? node.data.isBestPath : false,
      },
    }));
  }, [initialNodes, highlightBestPath]);

  // 更新边样式
  const edgesWithHighlight = useMemo(() => {
    if (!highlightBestPath) {
      return initialEdges.map(edge => ({
        ...edge,
        animated: false,
        style: {
          ...edge.style,
          stroke: '#6b7280',
          strokeWidth: 2,
        },
      }));
    }
    return initialEdges;
  }, [initialEdges, highlightBestPath]);

  const [nodes, setNodes, onNodesChange] = useNodesState(nodesWithCallbacks);
  const [edges, setEdges, onEdgesChange] = useEdgesState(edgesWithHighlight);

  // 当数据变化时更新
  useEffect(() => {
    setNodes(nodesWithCallbacks);
    setEdges(edgesWithHighlight);
  }, [nodesWithCallbacks, edgesWithHighlight, setNodes, setEdges]);

  // 自动适应视图
  useEffect(() => {
    const timer = setTimeout(() => {
      fitView({ padding: 0.2, duration: 300 });
    }, 100);
    return () => clearTimeout(timer);
  }, [nodes, fitView]);

  // 全部展开/折叠
  const handleExpandAll = () => {
    setCollapsedNodes(new Set());
  };

  const handleCollapseAll = () => {
    const nodesWithChildren = new Set<string>();
    experimentNodes.forEach(node => {
      if (node.parent_id) {
        nodesWithChildren.add(node.parent_id);
      }
    });
    setCollapsedNodes(nodesWithChildren);
  };

  if (!experimentNodes || experimentNodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-[600px] bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <p className="text-gray-500">暂无迭代数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 控制栏 */}
      <div className="flex items-center justify-between bg-white rounded-lg p-3 shadow-sm border">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">
            共 {experimentNodes.length} 个节点
          </span>
          {bestMetricValue !== null && bestMetricValue !== undefined && (
            <span className="text-sm text-gray-500">
              | 最佳指标: <span className="font-semibold text-green-600">{bestMetricValue.toFixed(6)}</span>
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setHighlightBestPath(!highlightBestPath)}
            className={highlightBestPath ? 'bg-green-50 border-green-300' : ''}
          >
            <Star className={`w-4 h-4 mr-1 ${highlightBestPath ? 'text-green-600' : ''}`} />
            最优路径
          </Button>
          <Button variant="outline" size="sm" onClick={handleExpandAll}>
            展开全部
          </Button>
          <Button variant="outline" size="sm" onClick={handleCollapseAll}>
            折叠全部
          </Button>
        </div>
      </div>

      {/* 图例 */}
      <div className="flex items-center gap-6 bg-white rounded-lg p-3 shadow-sm border text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-gradient-to-r from-amber-200 to-amber-400 border-2 border-amber-500"></div>
          <span className="text-gray-600">最佳节点</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-gradient-to-r from-green-200 to-green-400 border-2 border-green-500"></div>
          <span className="text-gray-600">最优路径</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-gradient-to-r from-red-200 to-red-400 border-2 border-red-500"></div>
          <span className="text-gray-600">执行错误</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-gradient-to-r from-blue-100 to-blue-300 border-2 border-blue-500"></div>
          <span className="text-gray-600">正常节点</span>
        </div>
      </div>

      {/* 图形区域 */}
      <div className="h-[600px] bg-gray-50 rounded-lg border shadow-inner">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.1}
          maxZoom={2}
          defaultEdgeOptions={{
            type: 'smoothstep',
          }}
        >
          <Background color="#e5e7eb" gap={20} />
          <Controls 
            showZoom={true}
            showFitView={true}
            showInteractive={false}
          />
          <MiniMap 
            nodeColor={(node) => {
              const data = node.data as IterationNodeData;
              if (data.isBest) return '#f59e0b';
              if (data.isBestPath) return '#10b981';
              if (data.isBuggy) return '#ef4444';
              return '#0ea5e9';
            }}
            maskColor="rgba(0, 0, 0, 0.1)"
          />
        </ReactFlow>
      </div>

      {/* 节点详情面板 */}
      <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
    </div>
  );
};

// 导出的主组件 (带 Provider)
interface IterationTreeGraphProps {
  experimentNodes: ExperimentNode[];
  bestMetricValue?: number;
}

export const IterationTreeGraph = ({ experimentNodes, bestMetricValue }: IterationTreeGraphProps) => {
  return (
    <ReactFlowProvider>
      <IterationTreeGraphContent 
        experimentNodes={experimentNodes} 
        bestMetricValue={bestMetricValue}
      />
    </ReactFlowProvider>
  );
};

export default IterationTreeGraph;
