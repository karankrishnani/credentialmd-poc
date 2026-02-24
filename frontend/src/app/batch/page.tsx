'use client';

import { useState, useCallback, useRef } from 'react';

// API base URL - configurable for development
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface BatchResult {
  npi_number: string;
  provider_name: string | null;
  verification_status: string;
  confidence_score: number | null;
  discrepancies: string[];
}

interface BatchStatus {
  batch_id: string;
  total: number;
  completed: number;
  status: string;
  results: BatchResult[];
}

interface UploadedCsv {
  fileName: string;
  npis: string[];
  file: File;
}

export default function BatchPage() {
  const [npis, setNpis] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);
  const [uploadedCsv, setUploadedCsv] = useState<UploadedCsv | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle CSV file selection
  const handleFileSelect = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setError('');

    try {
      const text = await file.text();
      const lines = text.trim().split('\n');

      // Find the NPI column
      const header = lines[0].toLowerCase();
      const columns = header.split(',').map(col => col.trim().replace(/"/g, ''));
      const npiColumnIndex = columns.indexOf('npi');

      if (npiColumnIndex === -1) {
        throw new Error('CSV must have an "npi" column');
      }

      // Parse NPIs from data rows
      const parsedNpis: string[] = [];
      for (let i = 1; i < lines.length; i++) {
        const row = lines[i].split(',');
        if (row.length > npiColumnIndex) {
          const npi = row[npiColumnIndex].trim().replace(/"/g, '');
          if (npi.length === 10 && /^\d+$/.test(npi)) {
            parsedNpis.push(npi);
          }
        }
      }

      if (parsedNpis.length === 0) {
        throw new Error('No valid 10-digit NPIs found in CSV');
      }

      if (parsedNpis.length > 20) {
        throw new Error('Maximum 20 NPIs per batch. CSV contains ' + parsedNpis.length + ' NPIs.');
      }

      setUploadedCsv({
        fileName: file.name,
        npis: parsedNpis,
        file: file,
      });

      // Clear the text input when CSV is uploaded
      setNpis('');

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse CSV');
      setUploadedCsv(null);
    }

    // Reset the file input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Clear uploaded CSV
  const handleClearCsv = useCallback(() => {
    setUploadedCsv(null);
  }, []);

  const handleRunBatch = useCallback(async () => {
    setIsLoading(true);
    setError('');
    setBatchStatus(null);

    try {
      // Get NPIs from uploaded CSV or textarea
      let npiList: string[];

      if (uploadedCsv) {
        npiList = uploadedCsv.npis;
      } else {
        // Parse NPIs from textarea
        npiList = npis
          .split(/[\n,]/)
          .map(npi => npi.trim())
          .filter(npi => npi.length === 10 && /^\d+$/.test(npi));
      }

      if (npiList.length === 0) {
        throw new Error('No valid NPIs found. Enter 10-digit NPI numbers, one per line.');
      }

      if (npiList.length > 20) {
        throw new Error('Maximum 20 NPIs per batch');
      }

      // Start batch
      const response = await fetch(`${API_BASE_URL}/api/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ npis: npiList }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      const batchId = data.batch_id;

      // Initialize batch status with queued status for all NPIs
      setBatchStatus({
        batch_id: batchId,
        total: npiList.length,
        completed: 0,
        status: 'processing',
        results: npiList.map(npi => ({
          npi_number: npi,
          provider_name: null,
          verification_status: 'queued',
          confidence_score: null,
          discrepancies: [],
        })),
      });

      // Connect to SSE stream
      const eventSource = new EventSource(`${API_BASE_URL}/api/batch/${batchId}/stream`);

      eventSource.onmessage = (event) => {
        try {
          const eventData = JSON.parse(event.data);

          if (eventData.event === 'result') {
            setBatchStatus(prev => {
              if (!prev) return null;
              const newResults = [...prev.results];
              // Update the result at the completed index
              if (eventData.result && eventData.completed > 0) {
                newResults[eventData.completed - 1] = eventData.result;
              }
              return {
                ...prev,
                completed: eventData.completed,
                results: newResults,
              };
            });
          } else if (eventData.event === 'completed') {
            setBatchStatus(prev => ({
              ...prev!,
              status: 'completed',
              completed: eventData.completed,
              results: eventData.results || prev!.results,
            }));
            eventSource.close();
            setIsLoading(false);
            setUploadedCsv(null); // Clear uploaded CSV after batch completes
          }
        } catch (err) {
          console.error('SSE parse error:', err);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        // Fetch final status
        fetch(`${API_BASE_URL}/api/batch/${batchId}`)
          .then(res => res.json())
          .then(data => {
            setBatchStatus({
              batch_id: batchId,
              total: data.total,
              completed: data.completed,
              status: data.status,
              results: data.results,
            });
          })
          .catch(console.error)
          .finally(() => setIsLoading(false));
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start batch');
      setIsLoading(false);
    }
  }, [npis]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'verified':
        return 'bg-success-100 text-success-700 border-success-200';
      case 'flagged':
        return 'bg-warning-100 text-warning-700 border-warning-200';
      case 'failed':
        return 'bg-danger-100 text-danger-700 border-danger-200';
      case 'escalated':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'queued':
      case 'pending':
        return 'bg-slate-100 text-slate-600 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

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

      {/* Error Message */}
      {error && (
        <div className="bg-danger-50 border border-danger-200 rounded-lg p-4 text-danger-700">
          {error}
        </div>
      )}

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
            onClick={handleRunBatch}
            disabled={isLoading || !npis.trim() || !!uploadedCsv}
            className="mt-4 w-full bg-primary-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Processing...' : 'Run Batch'}
          </button>
        </div>

        {/* CSV Upload */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-800 mb-4">
            Upload CSV
          </h3>
          {uploadedCsv ? (
            // Show uploaded CSV info
            <div className="border-2 border-success-300 bg-success-50 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <svg
                    className="h-10 w-10 text-success-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div>
                    <p className="font-medium text-slate-800">{uploadedCsv.fileName}</p>
                    <p className="text-sm text-success-700">
                      {uploadedCsv.npis.length} physician{uploadedCsv.npis.length !== 1 ? 's' : ''} found
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleClearCsv}
                  disabled={isLoading}
                  className="text-slate-400 hover:text-slate-600 disabled:opacity-50"
                  title="Remove file"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <button
                onClick={handleRunBatch}
                disabled={isLoading}
                className="mt-4 w-full bg-success-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-success-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Processing...' : `Verify ${uploadedCsv.npis.length} Physicians`}
              </button>
            </div>
          ) : (
            // Show file upload dropzone
            <div
              className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary-400 hover:bg-slate-50 transition-colors"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                e.currentTarget.classList.add('border-primary-400', 'bg-slate-50');
              }}
              onDragLeave={(e) => {
                e.currentTarget.classList.remove('border-primary-400', 'bg-slate-50');
              }}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove('border-primary-400', 'bg-slate-50');
                const file = e.dataTransfer.files[0];
                if (file && file.name.endsWith('.csv')) {
                  // Create a synthetic event for handleFileSelect
                  const dataTransfer = new DataTransfer();
                  dataTransfer.items.add(file);
                  if (fileInputRef.current) {
                    fileInputRef.current.files = dataTransfer.files;
                    fileInputRef.current.dispatchEvent(new Event('change', { bubbles: true }));
                  }
                } else {
                  setError('Please drop a CSV file');
                }
              }}
            >
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
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                disabled={isLoading}
                onChange={handleFileSelect}
              />
              <button
                type="button"
                disabled={isLoading}
                className="mt-4 px-4 py-2 text-sm font-medium text-primary-600 bg-primary-50 rounded-lg hover:bg-primary-100 disabled:opacity-50"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                Select File
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-lg font-medium text-slate-800">
            Batch Results
          </h3>
          {batchStatus && (
            <div className="flex items-center gap-4">
              {batchStatus.status === 'processing' ? (
                <>
                  <span className="text-sm text-slate-500">
                    Processing {batchStatus.completed + 1} of {batchStatus.total}...
                  </span>
                  <div className="w-4 h-4 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
                </>
              ) : (
                <span className="text-sm text-slate-500">
                  {batchStatus.completed} / {batchStatus.total} completed
                </span>
              )}
              {batchStatus.status === 'completed' && (
                <a
                  href={`${API_BASE_URL}/api/batch/${batchStatus.batch_id}/export`}
                  className="text-sm text-primary-600 hover:text-primary-700"
                >
                  Export CSV
                </a>
              )}
            </div>
          )}
        </div>

        {batchStatus ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    NPI
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Provider Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Confidence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Discrepancies
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {batchStatus.results.map((result, index) => (
                  <tr key={index} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-sm text-slate-800">
                      {result.npi_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-800">
                      {result.provider_name || (result.verification_status === 'queued' || result.verification_status === 'pending' ? '...' : 'Unknown')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(result.verification_status)}`}>
                        {result.verification_status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                      {result.confidence_score !== null ? `${result.confidence_score}%` : '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600 max-w-xs truncate">
                      {result.discrepancies && result.discrepancies.length > 0
                        ? result.discrepancies.join(', ')
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-center text-slate-500">
            <p>No batch in progress. Enter NPIs or upload a CSV to start.</p>
          </div>
        )}
      </div>
    </div>
  );
}
