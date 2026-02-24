'use client';

import { useState } from 'react';

export default function VerifyPage() {
  const [npi, setNpi] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate NPI
    if (!npi || npi.length !== 10 || !/^\d+$/.test(npi)) {
      setError('Please enter a valid 10-digit NPI number');
      return;
    }

    setIsLoading(true);

    try {
      // TODO: Call API to start verification
      console.log('Starting verification for NPI:', npi);
      // const response = await fetch('/api/verify', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ npi }),
      // });
      // const data = await response.json();
      // // Handle response, start SSE subscription
    } catch (err) {
      setError('Failed to start verification');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNpiChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Only allow digits
    const value = e.target.value.replace(/\D/g, '').slice(0, 10);
    setNpi(value);
    setError('');
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

      {/* Pipeline Tracker (placeholder) */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 max-w-2xl">
        <h3 className="text-lg font-medium text-slate-800 mb-4">
          Verification Pipeline
        </h3>
        <div className="space-y-3">
          {['NPI Lookup', 'License Check', 'Exclusion Check', 'Analysis', 'Result'].map(
            (step, index) => (
              <div
                key={step}
                className="flex items-center gap-3 py-2 px-3 rounded-lg bg-slate-50"
              >
                <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 text-sm">
                  {index + 1}
                </div>
                <span className="text-slate-600">{step}</span>
              </div>
            )
          )}
        </div>
        <p className="mt-4 text-sm text-slate-500 text-center">
          Enter an NPI number and click Verify to start
        </p>
      </div>
    </div>
  );
}
