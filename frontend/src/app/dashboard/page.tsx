'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts';

// API base URL - configurable for development
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CostDataPoint {
  timestamp: string;
  cost: number;
}

interface RetryStatistics {
  npi_retry_rate: number;
  dca_retry_rate: number;
  total_with_retries: number;
}

interface MetricsData {
  total_verifications: number;
  avg_cost_usd: number;
  avg_latency_ms: {
    npi: number;
    dca: number;
    leie: number;
    llm: number;
  };
  failure_rates: {
    npi: number;
    dca: number;
    leie: number;
  };
  outcome_distribution: {
    verified: number;
    flagged: number;
    failed: number;
    escalated: number;
  };
  cost_over_time?: CostDataPoint[];
  retry_statistics?: RetryStatistics;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchMetrics = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/metrics`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setMetrics(data);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();

    // Subscribe to metrics SSE stream for real-time updates
    let eventSource: EventSource | null = null;

    const connectSSE = () => {
      eventSource = new EventSource(`${API_BASE_URL}/api/metrics/stream`);

      eventSource.onmessage = (event) => {
        try {
          const eventData = JSON.parse(event.data);
          if (eventData.event === 'metrics') {
            setMetrics(eventData.data);
            setError('');
            setIsLoading(false);
          } else if (eventData.event === 'close') {
            // Reconnect after idle timeout
            eventSource?.close();
            setTimeout(connectSSE, 5000);
          }
        } catch (err) {
          // Ignore parse errors
        }
      };

      eventSource.addEventListener('metrics', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          setMetrics(data);
          setError('');
          setIsLoading(false);
        } catch (err) {
          // Ignore parse errors
        }
      });

      eventSource.onerror = () => {
        eventSource?.close();
        // Reconnect after 5 seconds on error
        setTimeout(connectSSE, 5000);
      };
    };

    connectSSE();

    // Fallback: refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);

    return () => {
      clearInterval(interval);
      eventSource?.close();
    };
  }, [fetchMetrics]);

  // Calculate total latency
  const totalLatency = metrics
    ? metrics.avg_latency_ms.npi + metrics.avg_latency_ms.dca + metrics.avg_latency_ms.leie + metrics.avg_latency_ms.llm
    : 0;

  // Calculate overall failure rate
  const overallFailureRate = metrics
    ? (metrics.failure_rates.npi + metrics.failure_rates.dca + metrics.failure_rates.leie) / 3
    : 0;

  // Calculate total outcomes
  const totalOutcomes = metrics
    ? metrics.outcome_distribution.verified +
      metrics.outcome_distribution.flagged +
      metrics.outcome_distribution.failed +
      metrics.outcome_distribution.escalated
    : 0;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-800">
            Dashboard
          </h2>
          <p className="mt-1 text-slate-600">
            Verification metrics and performance analytics
          </p>
        </div>
        <button
          onClick={fetchMetrics}
          disabled={isLoading}
          className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
        >
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-danger-50 border border-danger-200 rounded-lg p-4 text-danger-700">
          {error}
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Verifications"
          value={isLoading ? '...' : (metrics?.total_verifications ?? 0).toString()}
          subtitle="all time"
          color="blue"
        />
        <MetricCard
          title="Avg Cost"
          value={isLoading ? '...' : `$${(metrics?.avg_cost_usd ?? 0).toFixed(2)}`}
          subtitle="per verification"
          color="green"
        />
        <MetricCard
          title="Avg Latency"
          value={isLoading ? '...' : `${totalLatency}ms`}
          subtitle="total pipeline"
          color="amber"
        />
        <MetricCard
          title="Failure Rate"
          value={isLoading ? '...' : `${(overallFailureRate * 100).toFixed(1)}%`}
          subtitle="overall"
          color="red"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Latency by Source
          </h3>
          <div className="h-64">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-slate-400">
                Loading...
              </div>
            ) : metrics ? (
              <div className="space-y-4">
                <LatencyBar label="NPI" value={metrics.avg_latency_ms.npi} max={Math.max(...Object.values(metrics.avg_latency_ms))} color="blue" />
                <LatencyBar label="DCA" value={metrics.avg_latency_ms.dca} max={Math.max(...Object.values(metrics.avg_latency_ms))} color="green" />
                <LatencyBar label="LEIE" value={metrics.avg_latency_ms.leie} max={Math.max(...Object.values(metrics.avg_latency_ms))} color="amber" />
                <LatencyBar label="LLM" value={metrics.avg_latency_ms.llm} max={Math.max(...Object.values(metrics.avg_latency_ms))} color="purple" />
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400">
                No data yet
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Outcome Distribution
          </h3>
          <div className="h-64">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-slate-400">
                Loading...
              </div>
            ) : metrics && totalOutcomes > 0 ? (
              <div className="space-y-4">
                <OutcomeRow
                  label="Verified"
                  value={metrics.outcome_distribution.verified}
                  total={totalOutcomes}
                  color="success"
                />
                <OutcomeRow
                  label="Flagged"
                  value={metrics.outcome_distribution.flagged}
                  total={totalOutcomes}
                  color="warning"
                />
                <OutcomeRow
                  label="Failed"
                  value={metrics.outcome_distribution.failed}
                  total={totalOutcomes}
                  color="danger"
                />
                <OutcomeRow
                  label="Escalated"
                  value={metrics.outcome_distribution.escalated}
                  total={totalOutcomes}
                  color="purple"
                />
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400">
                No data yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Failure Rates Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h3 className="text-lg font-medium text-slate-800 mb-4">
          Failure Rates by Source
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {isLoading ? (
            <div className="col-span-3 flex items-center justify-center text-slate-400 py-8">
              Loading...
            </div>
          ) : metrics ? (
            <>
              <div className="bg-red-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">NPI Registry</span>
                  <span className="text-lg font-semibold text-red-600">
                    {(metrics.failure_rates.npi * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2 h-2 bg-red-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(metrics.failure_rates.npi * 100, 100)}%` }}
                  />
                </div>
              </div>
              <div className="bg-orange-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">DCA Board</span>
                  <span className="text-lg font-semibold text-orange-600">
                    {(metrics.failure_rates.dca * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2 h-2 bg-orange-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-orange-500 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(metrics.failure_rates.dca * 100, 100)}%` }}
                  />
                </div>
              </div>
              <div className="bg-amber-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">LEIE Check</span>
                  <span className="text-lg font-semibold text-amber-600">
                    {(metrics.failure_rates.leie * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2 h-2 bg-amber-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(metrics.failure_rates.leie * 100, 100)}%` }}
                  />
                </div>
              </div>
            </>
          ) : (
            <div className="col-span-3 flex items-center justify-center text-slate-400 py-8">
              No data yet
            </div>
          )}
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Cost Over Time
          </h3>
          <div className="h-64">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-slate-400">
                Loading...
              </div>
            ) : metrics?.cost_over_time && metrics.cost_over_time.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={metrics.cost_over_time.map((point, index) => ({
                    ...point,
                    index: index + 1,
                  }))}
                  margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="index"
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <YAxis
                    tickFormatter={(value) => `$${value.toFixed(2)}`}
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <Tooltip
                    formatter={(value: number) => [`$${value.toFixed(4)}`, 'Cost']}
                    labelFormatter={(label) => `Verification #${label}`}
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="cost"
                    stroke="#2563eb"
                    strokeWidth={2}
                    dot={{ fill: '#2563eb', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, fill: '#1d4ed8' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400">
                No cost data yet
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Retry Statistics
          </h3>
          <div className="h-64">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-slate-400">
                Loading...
              </div>
            ) : metrics?.retry_statistics ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[
                    { source: 'NPI', rate: metrics.retry_statistics.npi_retry_rate * 100 },
                    { source: 'DCA', rate: metrics.retry_statistics.dca_retry_rate * 100 },
                  ]}
                  margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="source"
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <YAxis
                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    axisLine={{ stroke: '#cbd5e1' }}
                    domain={[0, 100]}
                  />
                  <Tooltip
                    formatter={(value: number) => [`${value.toFixed(1)}%`, 'Retry Rate']}
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
                    <Cell fill="#3b82f6" />
                    <Cell fill="#22c55e" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400">
                No retry data yet
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  color,
}: {
  title: string;
  value: string;
  subtitle: string;
  color: 'blue' | 'green' | 'amber' | 'red';
}) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-600',
    green: 'bg-green-50 border-green-200 text-green-600',
    amber: 'bg-amber-50 border-amber-200 text-amber-600',
    red: 'bg-red-50 border-red-200 text-red-600',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <p className={`mt-2 text-3xl font-semibold ${colorClasses[color].split(' ')[2]}`}>
        {value}
      </p>
      <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
    </div>
  );
}

function LatencyBar({
  label,
  value,
  max,
  color,
}: {
  label: string;
  value: number;
  max: number;
  color: 'blue' | 'green' | 'amber' | 'purple';
}) {
  const percentage = max > 0 ? (value / max) * 100 : 0;
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    amber: 'bg-amber-500',
    purple: 'bg-purple-500',
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-slate-600">{label}</span>
        <span className="text-slate-800 font-medium">{value}ms</span>
      </div>
      <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorClasses[color]} rounded-full transition-all duration-500`}
          style={{ width: `${Math.max(percentage, 2)}%` }}
        />
      </div>
    </div>
  );
}

function OutcomeRow({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: 'success' | 'warning' | 'danger' | 'purple';
}) {
  const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
  const colorClasses = {
    success: 'bg-success-500 text-success-700',
    warning: 'bg-warning-500 text-warning-700',
    danger: 'bg-danger-500 text-danger-700',
    purple: 'bg-purple-500 text-purple-700',
  };
  const bgColorClasses = {
    success: 'bg-success-100',
    warning: 'bg-warning-100',
    danger: 'bg-danger-100',
    purple: 'bg-purple-100',
  };

  return (
    <div className="flex items-center gap-4">
      <div className={`w-3 h-3 rounded-full ${colorClasses[color].split(' ')[0]}`} />
      <div className="flex-1">
        <div className="flex justify-between text-sm">
          <span className="text-slate-600">{label}</span>
          <span className={`font-medium ${colorClasses[color].split(' ')[1]}`}>
            {value} ({percentage}%)
          </span>
        </div>
        <div className="mt-1 h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full ${colorClasses[color].split(' ')[0]} rounded-full transition-all duration-500`}
            style={{ width: `${parseFloat(percentage)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
