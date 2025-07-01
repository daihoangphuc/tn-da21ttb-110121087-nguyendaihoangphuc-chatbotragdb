"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from "recharts";
import { Brain, TrendingUp, BookOpen, Lightbulb, X, Target, Clock } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { fetchApi } from "@/lib/api";

interface DashboardData {
  user_id: string;
  period: {
    weeks: number;
    from: string;
    to: string;
  };
  weekly_metrics: Array<{
    metric_id: string;
    user_id: string;
    date_week: string;
    total_questions: number;
    bloom_distribution: Record<string, number>;
    topics_covered: string[];
    autonomy_score: number;
    most_frequent_topic: string;
  }>;
  recommendations: Array<{
    recommendation_id: string;
    title: string;
    description: string;
    recommendation_type: string;
    target_topic: string;
    status: string;
  }>;
  summary: {
    total_questions: number;
    topics_learned: number;
    current_trend: string;
    latest_autonomy_score: number;
  };
}

export function SimpleLearningDashboard() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();
  
  useEffect(() => {
    loadDashboard();
  }, []);
  
  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await fetchApi('/learning/dashboard');
      setDashboardData(data);
    } catch (error) {
      console.error('Error loading dashboard:', error);
      setError(error instanceof Error ? error.message : 'Có lỗi xảy ra khi tải dashboard');
    } finally {
      setLoading(false);
    }
  };
  
  const dismissRecommendation = async (id: string) => {
    try {
      await fetchApi(`/learning/recommendations/${id}/dismiss`, {
        method: 'POST'
      });
      
      toast({
        title: "Thành công",
        description: "Đã ẩn gợi ý",
      });
      
      loadDashboard(); // Reload
    } catch (error) {
      console.error('Error dismissing recommendation:', error);
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Không thể ẩn gợi ý",
      });
    }
  };
  
  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-6" suppressHydrationWarning={true}>
        <div className="space-y-6" suppressHydrationWarning={true}>
          <div className="h-8 bg-gray-200 rounded animate-pulse" suppressHydrationWarning={true}></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4" suppressHydrationWarning={true}>
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="h-20 bg-gray-200 rounded animate-pulse" suppressHydrationWarning={true}></div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto p-6" suppressHydrationWarning={true}>
        <Card>
          <CardContent className="p-6 text-center" suppressHydrationWarning={true}>
            <div className="text-red-500 text-lg font-semibold mb-2">Lỗi khi tải dashboard</div>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={loadDashboard}>Thử lại</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="max-w-6xl mx-auto p-6" suppressHydrationWarning={true}>
        <Card>
          <CardContent className="p-6 text-center" suppressHydrationWarning={true}>
            <div className="text-gray-500">Không có dữ liệu dashboard</div>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  const { summary, weekly_metrics, recommendations } = dashboardData;
  
  // Chuẩn bị dữ liệu cho charts
  const bloomData = weekly_metrics.length > 0 ? 
    Object.entries(weekly_metrics[0].bloom_distribution || {}).map(([level, count]) => ({
      level, 
      count,
      fill: getBloomColor(level)
    })) : [];
  
  // Weekly trend data
  const weeklyTrendData = weekly_metrics
    .slice(0, 4)
    .reverse()
    .map(metric => ({
      week: new Date(metric.date_week).toLocaleDateString('vi-VN', { month: 'short', day: 'numeric' }),
      questions: metric.total_questions,
      autonomy: Math.round(metric.autonomy_score * 100)
    }));
  
  function getBloomColor(level: string): string {
    const colors: Record<string, string> = {
      'Remember': '#ef4444',
      'Understand': '#f97316', 
      'Apply': '#eab308',
      'Analyze': '#22c55e',
      'Evaluate': '#3b82f6',
      'Create': '#8b5cf6'
    };
    return colors[level] || '#6b7280';
  }
  
  function getTrendIcon(trend: string) {
    switch (trend) {
      case 'improving':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      default:
        return <Target className="h-4 w-4 text-blue-500" />;
    }
  }
  
  function getTrendText(trend: string) {
    switch (trend) {
      case 'improving':
        return 'Đang tiến bộ';
      case 'stable':
        return 'Ổn định';
      default:
        return 'Cần theo dõi';
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8" suppressHydrationWarning={true}>
      {/* Academic Overview Card */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-8" suppressHydrationWarning={true}>
        <div className="flex items-center space-x-3 mb-6">
          <div className="p-3 bg-blue-100 rounded-lg">
            <BookOpen className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Tổng quan Học tập</h2>
            <p className="text-gray-600">Phân tích trong {dashboardData.period.weeks} tuần gần đây • Cập nhật liên tục</p>
          </div>
        </div>
        
        {/* Academic Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-6 border border-blue-200">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 bg-blue-500 rounded-lg">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-blue-800">{summary.total_questions}</div>
                <div className="text-sm font-medium text-blue-600">Câu hỏi đã đặt</div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <div className="h-2 w-2 bg-blue-500 rounded-full"></div>
              <span className="text-sm text-blue-700">{dashboardData.period.weeks} tuần gần đây</span>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-xl p-6 border border-emerald-200">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 bg-emerald-500 rounded-lg">
                <Brain className="h-5 w-5 text-white" />
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-emerald-800">{summary.topics_learned}</div>
                <div className="text-sm font-medium text-emerald-600">Chủ đề khám phá</div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <div className="h-2 w-2 bg-emerald-500 rounded-full"></div>
              <span className="text-sm text-emerald-700">Lĩnh vực CSDL</span>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-violet-50 to-violet-100 rounded-xl p-6 border border-violet-200">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 bg-violet-500 rounded-lg">
                <TrendingUp className="h-5 w-5 text-white" />
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-violet-800">
                  {Math.round(summary.latest_autonomy_score * 100)}%
                </div>
                <div className="text-sm font-medium text-violet-600">Tư duy cao</div>
              </div>
            </div>
            <div className="w-full bg-violet-200 rounded-full h-2">
              <div 
                className="bg-violet-500 h-2 rounded-full transition-all duration-300" 
                style={{ width: `${summary.latest_autonomy_score * 100}%` }}
              ></div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-xl p-6 border border-amber-200">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 bg-amber-500 rounded-lg">
                {getTrendIcon(summary.current_trend)}
              </div>
              <div className="text-right">
                <Badge variant={summary.current_trend === 'improving' ? 'default' : 'secondary'} className="mb-2">
                  {getTrendText(summary.current_trend)}
                </Badge>
                <div className="text-sm font-medium text-amber-600">Xu hướng học tập</div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <div className="h-2 w-2 bg-amber-500 rounded-full"></div>
              <span className="text-sm text-amber-700">So với tuần trước</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Academic Analytics Section */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Bloom Taxonomy Analysis */}
        {bloomData.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center space-x-3 mb-6">
              <div className="p-2 bg-indigo-100 rounded-lg">
                <Brain className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-gray-900">Phân tích</h3>
                <p className="text-sm text-gray-600">Phân bố mức độ tư duy nhận thức (tuần này)</p>
              </div>
            </div>
            <div className="relative">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={bloomData}
                    dataKey="count"
                    nameKey="level"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    innerRadius={40}
                    label={({level, count, percent}) => `${level}: ${count} (${(percent * 100).toFixed(0)}%)`}
                    labelLine={false}
                  >
                    {bloomData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value, name) => [`${value} câu hỏi`, name]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
              
              {/* Bloom Levels Legend */}
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                    <span className="text-gray-700">Remember (Nhớ)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                    <span className="text-gray-700">Understand (Hiểu)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                    <span className="text-gray-700">Apply (Áp dụng)</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    <span className="text-gray-700">Analyze (Phân tích)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                    <span className="text-gray-700">Evaluate (Đánh giá)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                    <span className="text-gray-700">Create (Sáng tạo)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Learning Progress Trends */}
        {weeklyTrendData.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center space-x-3 mb-6">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <TrendingUp className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-gray-900">Xu hướng Học tập</h3>
                <p className="text-sm text-gray-600">Hoạt động học tập {dashboardData.period.weeks} tuần gần đây</p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={weeklyTrendData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <XAxis 
                  dataKey="week" 
                  tick={{ fontSize: 12 }}
                  axisLine={{ stroke: '#e2e8f0' }}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  axisLine={{ stroke: '#e2e8f0' }}
                />
                <Tooltip 
                  formatter={(value, name) => [`${value} câu hỏi`, 'Số lượng câu hỏi']}
                  labelFormatter={(label) => `Tuần: ${label}`}
                  contentStyle={{
                    backgroundColor: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px'
                  }}
                />
                <Bar 
                  dataKey="questions" 
                  fill="url(#colorGradient)" 
                  radius={[4, 4, 0, 0]}
                />
                <defs>
                  <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
      
      {/* Academic Recommendations */}
      {recommendations.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Lightbulb className="h-5 w-5 text-yellow-600" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Khuyến nghị Học thuật</h3>
              <p className="text-sm text-gray-600">Gợi ý cá nhân hóa dựa trên phân tích học tập của bạn</p>
            </div>
          </div>
          <div className="space-y-4">
            {recommendations.map((rec) => (
              <div key={rec.recommendation_id} className="group relative bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5 hover:shadow-md transition-all duration-300">
                <div className="flex items-start justify-between">
                  <div className="flex-1 pr-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <Target className="h-4 w-4 text-blue-600" />
                      <h4 className="font-semibold text-blue-900">{rec.title}</h4>
                    </div>
                    <p className="text-sm text-blue-800 leading-relaxed mb-3">{rec.description}</p>
                    {rec.target_topic && (
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline" className="text-xs border-blue-300 text-blue-700 bg-blue-50">
                          📚 {rec.target_topic}
                        </Badge>
                        <span className="text-xs text-blue-600">• Mức ưu tiên: {rec.recommendation_type === 'advance' ? 'Cao' : 'Trung bình'}</span>
                      </div>
                    )}
                  </div>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => dismissRecommendation(rec.recommendation_id)}
                    className="opacity-0 group-hover:opacity-100 text-blue-600 hover:text-blue-800 hover:bg-blue-100 transition-all duration-200"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Empty State - Academic Style */}
      {summary.total_questions === 0 && (
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-12 text-center">
          <div className="max-w-md mx-auto">
            <div className="p-6 bg-gray-50 rounded-full w-24 h-24 mx-auto mb-6 flex items-center justify-center">
              <Clock className="h-12 w-12 text-gray-400" />
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-4">Bắt đầu hành trình học tập</h3>
            <p className="text-gray-600 mb-6 leading-relaxed">
              Dashboard phân tích này sẽ hiển thị tiến bộ học tập của bạn sau khi bạn bắt đầu tương tác với hệ thống. 
              Hãy đặt câu hỏi đầu tiên để xem phân tích chi tiết về quá trình học tập!
            </p>
            <div className="space-y-3">
              <Button asChild className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-medium">
                <a href="/">🚀 Bắt đầu học tập ngay</a>
              </Button>
              <p className="text-sm text-gray-500">
                💡 Mẹo: Hãy đặt câu hỏi về SQL, thiết kế CSDL, hoặc các khái niệm liên quan
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 