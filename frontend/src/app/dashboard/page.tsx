'use client';

export default function DashboardPage() {
  // Placeholder metrics
  const metrics = {
    totalVerifications: 0,
    avgCost: 0.0,
    avgLatency: 0,
    failureRate: 0.0,
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-semibold text-slate-800">
          Dashboard
        </h2>
        <p className="mt-1 text-slate-600">
          Verification metrics and performance analytics
        </p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Verifications"
          value={metrics.totalVerifications.toString()}
          subtitle="all time"
          color="blue"
        />
        <MetricCard
          title="Avg Cost"
          value={`$${metrics.avgCost.toFixed(2)}`}
          subtitle="per verification"
          color="green"
        />
        <MetricCard
          title="Avg Latency"
          value={`${metrics.avgLatency}ms`}
          subtitle="total pipeline"
          color="amber"
        />
        <MetricCard
          title="Failure Rate"
          value={`${metrics.failureRate.toFixed(1)}%`}
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
          <div className="h-64 flex items-center justify-center text-slate-400">
            {/* Placeholder for Recharts BarChart */}
            <p>No data yet</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Outcome Distribution
          </h3>
          <div className="h-64 flex items-center justify-center text-slate-400">
            {/* Placeholder for Recharts PieChart */}
            <p>No data yet</p>
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Cost Over Time
          </h3>
          <div className="h-64 flex items-center justify-center text-slate-400">
            {/* Placeholder for Recharts LineChart */}
            <p>No data yet</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Retry Statistics
          </h3>
          <div className="h-64 flex items-center justify-center text-slate-400">
            {/* Placeholder for Recharts BarChart */}
            <p>No data yet</p>
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
