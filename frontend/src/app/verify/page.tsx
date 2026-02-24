'use client';

import { useState, useCallback, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

// API base URL - configurable for development
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Pipeline step definitions
const PIPELINE_STEPS = [
  { id: 'npi_lookup', name: 'NPI Lookup', description: 'Fetching NPI Registry data' },
  { id: 'parallel_lookups', name: 'License & Exclusion Check', description: 'Checking DCA and LEIE' },
  { id: 'discrepancy_detection', name: 'Analysis', description: 'AI analyzing data sources' },
  { id: 'route_decision_node', name: 'Decision', description: 'Determining verification outcome' },
  { id: 'finalize', name: 'Result', description: 'Finalizing verification' },
];

type StepStatus = 'pending' | 'active' | 'completed' | 'error';

interface PipelineStep {
  id: string;
  name: string;
  description: string;
  status: StepStatus;
}

interface VerificationResult {
  id: string;
  npi_number: string;
  provider_name: string | null;
  provider_first_name: string | null;
  provider_last_name: string | null;
  provider_credential: string | null;
  provider_specialty: string | null;
  license_number: string | null;
  license_state: string | null;
  verification_status: string;
  confidence_score: number | null;
  confidence_reasoning: string | null;
  discrepancies: string[];
  board_license_status: string | null;
  board_expiration_date: string | null;
  leie_match: boolean;
  needs_human_review: boolean;
  human_review_reason: string | null;
  step_latencies: Record<string, number>;
  errors: string[];
}

export default function VerifyPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [npi, setNpi] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [steps, setSteps] = useState<PipelineStep[]>(
    PIPELINE_STEPS.map(s => ({ ...s, status: 'pending' as StepStatus }))
  );
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [verificationId, setVerificationId] = useState<string | null>(null);

  // Load verification result from URL parameter on mount
  useEffect(() => {
    const id = searchParams.get('id');
    if (id && !result) {
      setIsLoading(true);
      fetch(`${API_BASE_URL}/api/verify/${id}`)
        .then(res => {
          if (!res.ok) throw new Error('Verification not found');
          return res.json();
        })
        .then(data => {
          setResult(data);
          setNpi(data.npi_number || '');
          setVerificationId(id);
          setSteps(prev => prev.map(s => ({ ...s, status: 'completed' as StepStatus })));
        })
        .catch(err => {
          console.error('Failed to load verification:', err);
          setError('Failed to load verification result. It may have expired or been deleted.');
          // Clear the invalid ID from URL
          router.replace('/verify');
        })
        .finally(() => setIsLoading(false));
    }
  }, [searchParams, result, router]);

  const resetPipeline = useCallback(() => {
    setSteps(PIPELINE_STEPS.map(s => ({ ...s, status: 'pending' as StepStatus })));
    setResult(null);
    setVerificationId(null);
    setError('');
    // Clear URL parameter when resetting
    router.replace('/verify');
  }, [router]);

  const updateStepStatus = useCallback((stepId: string, status: StepStatus) => {
    setSteps(prev => prev.map(step =>
      step.id === stepId ? { ...step, status } : step
    ));
  }, []);

  const markStepsUpTo = useCallback((stepId: string, status: StepStatus) => {
    setSteps(prev => {
      const stepIndex = prev.findIndex(s => s.id === stepId);
      return prev.map((step, index) => {
        if (index < stepIndex) {
          return { ...step, status: 'completed' as StepStatus };
        } else if (index === stepIndex) {
          return { ...step, status };
        }
        return step;
      });
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    resetPipeline();

    // Validate NPI
    if (!npi || npi.length !== 10 || !/^\d+$/.test(npi)) {
      setError('Please enter a valid 10-digit NPI number');
      return;
    }

    setIsLoading(true);

    try {
      // Start verification
      const response = await fetch(`${API_BASE_URL}/api/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ npi }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setVerificationId(data.verification_id);

      // Mark first step as active
      updateStepStatus('npi_lookup', 'active');

      // Connect to SSE for real-time updates
      const eventSource = new EventSource(
        `${API_BASE_URL}/api/verify/${data.verification_id}/stream`
      );

      eventSource.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);

          if (update.step === 'complete') {
            // Mark all steps as completed and show result
            setSteps(prev => prev.map(s => ({ ...s, status: 'completed' as StepStatus })));
            setResult(update.data);
            eventSource.close();
            setIsLoading(false);
            // Update URL with verification ID for persistence
            router.replace(`/verify?id=${data.verification_id}`);
          } else if (update.step && update.step !== 'start') {
            // Mark current step as active and previous as completed
            markStepsUpTo(update.step, 'active');
          }
        } catch (err) {
          console.error('Failed to parse SSE event:', err);
        }
      };

      eventSource.onerror = async () => {
        eventSource.close();

        // Fallback: poll for result
        try {
          const resultResponse = await fetch(
            `${API_BASE_URL}/api/verify/${data.verification_id}`
          );
          if (resultResponse.ok) {
            const resultData = await resultResponse.json();
            setResult(resultData);
            setSteps(prev => prev.map(s => ({ ...s, status: 'completed' as StepStatus })));
            // Update URL with verification ID for persistence
            router.replace(`/verify?id=${data.verification_id}`);
          }
        } catch (pollErr) {
          setError('Connection lost. Please try again.');
        }
        setIsLoading(false);
      };

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start verification');
      setIsLoading(false);
    }
  };

  const handleNpiChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Only allow digits
    const value = e.target.value.replace(/\D/g, '').slice(0, 10);
    setNpi(value);
    setError('');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'verified':
        return 'bg-success-100 text-success-800 border-success-200';
      case 'flagged':
        return 'bg-warning-100 text-warning-800 border-warning-200';
      case 'failed':
        return 'bg-danger-100 text-danger-800 border-danger-200';
      case 'escalated':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const getConfidenceColor = (score: number | null) => {
    if (score === null) return 'text-slate-400';
    if (score >= 85) return 'text-success-600';
    if (score >= 60) return 'text-warning-600';
    return 'text-danger-600';
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-semibold text-slate-800">
          Verify Physician
        </h2>
        <p className="mt-1 text-slate-600">
          Enter a 10-digit NPI number to verify physician credentials
        </p>
      </div>

      {/* Verification Form */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="npi"
              className="block text-sm font-medium text-slate-700 mb-1"
            >
              NPI Number
            </label>
            <input
              type="text"
              id="npi"
              value={npi}
              onChange={handleNpiChange}
              placeholder="1003127655"
              className="npi-input w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-lg"
              disabled={isLoading}
            />
            {error && (
              <p className="mt-1 text-sm text-danger-600">{error}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading || !npi}
            className="w-full bg-primary-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-primary-700 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Verifying...
              </span>
            ) : (
              'Verify'
            )}
          </button>
        </form>
      </div>

      {/* Pipeline Tracker */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 max-w-2xl">
        <h3 className="text-lg font-medium text-slate-800 mb-4">
          Verification Pipeline
        </h3>
        <div className="space-y-3">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`flex items-center gap-3 py-2 px-3 rounded-lg transition-colors ${
                step.status === 'active'
                  ? 'bg-primary-50 border border-primary-200'
                  : step.status === 'completed'
                  ? 'bg-success-50 border border-success-200'
                  : step.status === 'error'
                  ? 'bg-danger-50 border border-danger-200'
                  : 'bg-slate-50'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-sm ${
                  step.status === 'active'
                    ? 'bg-primary-600 text-white'
                    : step.status === 'completed'
                    ? 'bg-success-600 text-white'
                    : step.status === 'error'
                    ? 'bg-danger-600 text-white'
                    : 'bg-slate-200 text-slate-500'
                }`}
              >
                {step.status === 'completed' ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : step.status === 'active' ? (
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  index + 1
                )}
              </div>
              <div className="flex-1">
                <span className={`font-medium ${
                  step.status === 'active'
                    ? 'text-primary-700'
                    : step.status === 'completed'
                    ? 'text-success-700'
                    : 'text-slate-600'
                }`}>
                  {step.name}
                </span>
                {step.status === 'active' && (
                  <p className="text-sm text-primary-600">{step.description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
        {!isLoading && !result && (
          <p className="mt-4 text-sm text-slate-500 text-center">
            Enter an NPI number and click Verify to start
          </p>
        )}
      </div>

      {/* Verification Result */}
      {result && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 max-w-2xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-slate-800">
              Verification Result
            </h3>
            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(result.verification_status)}`}>
              {result.verification_status.toUpperCase()}
            </span>
          </div>

          {/* Provider Info */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-slate-500">Provider Name</p>
                <p className="font-medium text-slate-800">{result.provider_name || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Credential</p>
                <p className="font-medium text-slate-800">{result.provider_credential || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">License Number</p>
                <p className="font-medium text-slate-800">{result.license_number || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Specialty</p>
                <p className="font-medium text-slate-800">{result.provider_specialty || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">License Status</p>
                <p className="font-medium text-slate-800">{result.board_license_status || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Expiration Date</p>
                <p className="font-medium text-slate-800">{result.board_expiration_date || 'N/A'}</p>
              </div>
            </div>

            {/* Confidence Score */}
            <div className="pt-4 border-t border-slate-200">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-500">Confidence Score</p>
                <p className={`text-2xl font-bold ${getConfidenceColor(result.confidence_score)}`}>
                  {result.confidence_score !== null ? `${result.confidence_score}%` : 'N/A'}
                </p>
              </div>
              {result.confidence_reasoning && (
                <p className="mt-2 text-sm text-slate-600 bg-slate-50 p-3 rounded-lg">
                  {result.confidence_reasoning}
                </p>
              )}
            </div>

            {/* Discrepancies */}
            {result.discrepancies && result.discrepancies.length > 0 && (
              <div className="pt-4 border-t border-slate-200">
                <p className="text-sm font-medium text-slate-700 mb-2">Discrepancies Found</p>
                <ul className="space-y-1">
                  {result.discrepancies.map((d, i) => (
                    <li key={i} className="text-sm text-danger-600 flex items-start gap-2">
                      <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* LEIE Match Warning */}
            {result.leie_match && (
              <div className="pt-4 border-t border-slate-200">
                <div className="bg-danger-50 border border-danger-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-danger-800">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <span className="font-medium">OIG LEIE Exclusion Found</span>
                  </div>
                  <p className="mt-1 text-sm text-danger-700">
                    This physician is on the federal exclusion list and cannot participate in Medicare, Medicaid, or other federal healthcare programs.
                  </p>
                </div>
              </div>
            )}

            {/* Human Review Required */}
            {result.needs_human_review && (
              <div className="pt-4 border-t border-slate-200">
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-purple-800">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <span className="font-medium">Human Review Required</span>
                  </div>
                  {result.human_review_reason && (
                    <p className="mt-1 text-sm text-purple-700">
                      Reason: {result.human_review_reason}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Latency Info */}
            {result.step_latencies && Object.keys(result.step_latencies).length > 0 && (
              <div className="pt-4 border-t border-slate-200">
                <p className="text-sm text-slate-500 mb-2">Processing Time</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(result.step_latencies).map(([key, value]) => (
                    <span key={key} className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">
                      {key}: {value}ms
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
