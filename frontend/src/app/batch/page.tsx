'use client';

import { useState } from 'react';

export default function BatchPage() {
  const [npis, setNpis] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-semibold text-slate-800">
          Batch Verification
        </h2>
        <p className="mt-1 text-slate-600">
          Verify multiple physicians at once (up to 20 NPIs per batch)
        </p>
      </div>

      {/* Input Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Text Input */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Enter NPI Numbers
          </h3>
          <textarea
            value={npis}
            onChange={(e) => setNpis(e.target.value)}
            placeholder="Enter one NPI per line:&#10;1003127655&#10;1588667638&#10;1497758544"
            className="npi-input w-full h-48 px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
            disabled={isLoading}
          />
          <button
            disabled={isLoading || !npis.trim()}
            className="mt-4 w-full bg-primary-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Run Batch
          </button>
        </div>

        {/* CSV Upload */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Upload CSV
          </h3>
          <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center">
            <svg
              className="mx-auto h-12 w-12 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="mt-2 text-sm text-slate-600">
              Drag and drop a CSV file, or click to browse
            </p>
            <p className="mt-1 text-xs text-slate-500">
              CSV should have an 'npi' column
            </p>
            <input
              type="file"
              accept=".csv"
              className="hidden"
              disabled={isLoading}
            />
            <button
              disabled={isLoading}
              className="mt-4 px-4 py-2 text-sm font-medium text-primary-600 bg-primary-50 rounded-lg hover:bg-primary-100 disabled:opacity-50"
            >
              Select File
            </button>
          </div>
        </div>
      </div>

      {/* Results Table (placeholder) */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h3 className="text-lg font-medium text-slate-800">
            Batch Results
          </h3>
        </div>
        <div className="p-6 text-center text-slate-500">
          <p>No batch in progress. Enter NPIs or upload a CSV to start.</p>
        </div>
      </div>
    </div>
  );
}
