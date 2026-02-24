'use client';

import { useState, useEffect, useCallback } from 'react';

// API base URL - configurable for development
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface HITLItem {
  id: string;
  npi_number: string;
  provider_name: string | null;
  provider_first_name: string | null;
  provider_last_name: string | null;
  provider_credential: string | null;
  provider_specialty: string | null;
  license_number: string | null;
  verification_status: string;
  confidence_score: number | null;
  confidence_reasoning: string | null;
  discrepancies: string[];
  board_license_status: string | null;
  leie_match: boolean;
  needs_human_review: boolean;
  human_review_reason: string | null;
  human_review_links: Array<{ label: string; url: string }>;
}

export default function ReviewPage() {
  const [queue, setQueue] = useState<HITLItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchQueue = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/hitl/queue`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setQueue(data);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch queue');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
    // Refresh every 10 seconds
    const interval = setInterval(fetchQueue, 10000);
    return () => clearInterval(interval);
  }, [fetchQueue]);

  const handleDecisionComplete = useCallback(() => {
    // Refresh the queue after a decision is made
    fetchQueue();
  }, [fetchQueue]);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-800">
            HITL Review Queue
          </h2>
          <p className="mt-1 text-slate-600">
            Verifications requiring human review and decision
          </p>
        </div>
        <button
          onClick={fetchQueue}
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

      {/* Queue */}
      {isLoading ? (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
          <div className="w-12 h-12 mx-auto border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
          <p className="mt-4 text-slate-600">Loading queue...</p>
        </div>
      ) : queue.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
          <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h3 className="mt-4 text-lg font-medium text-slate-800">
            No verifications pending review
          </h3>
          <p className="mt-2 text-slate-500">
            All escalated verifications have been processed.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-slate-500">
            {queue.length} verification{queue.length !== 1 ? 's' : ''} pending review
          </p>
          {queue.map((item) => (
            <HITLCard
              key={item.id}
              item={item}
              onDecisionComplete={handleDecisionComplete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface HITLCardProps {
  item: HITLItem;
  onDecisionComplete: () => void;
}

function HITLCard({ item, onDecisionComplete }: HITLCardProps) {
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState('');

  const handleDecision = async (decision: 'approved' | 'rejected' | 'needs_info') => {
    setIsSubmitting(true);
    setSubmitError('');
    setSubmitSuccess('');

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/verify/${item.id}/review`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision, notes }),
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
      }

      setSubmitSuccess(`Decision "${decision}" submitted successfully`);
      setTimeout(() => {
        onDecisionComplete();
      }, 1000);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to submit decision');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-medium text-slate-800">
            {item.provider_name || 'Unknown Provider'}
          </h3>
          <p className="text-sm text-slate-500 font-mono">
            NPI: {item.npi_number}
          </p>
          {item.license_number && (
            <p className="text-sm text-slate-500">
              License: {item.license_number}
            </p>
          )}
        </div>
        <span className="px-3 py-1 text-sm font-medium text-purple-700 bg-purple-100 rounded-full">
          Needs Review
        </span>
      </div>

      {/* Escalation Reason */}
      <div className="mt-4 p-4 bg-amber-50 rounded-lg border border-amber-200">
        <p className="text-sm font-medium text-amber-800">
          Reason for Escalation
        </p>
        <p className="mt-1 text-amber-700">
          {item.human_review_reason || 'Unknown reason'}
        </p>
      </div>

      {/* Evidence Summary */}
      <div className="mt-4">
        <p className="text-sm font-medium text-slate-700 mb-2">Collected Evidence</p>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="bg-slate-50 p-3 rounded-lg">
            <span className="text-slate-500">Status:</span>{' '}
            <span className="font-medium">{item.verification_status}</span>
          </div>
          {item.confidence_score !== null && (
            <div className="bg-slate-50 p-3 rounded-lg">
              <span className="text-slate-500">Confidence:</span>{' '}
              <span className="font-medium">{item.confidence_score}%</span>
            </div>
          )}
          {item.board_license_status && (
            <div className="bg-slate-50 p-3 rounded-lg">
              <span className="text-slate-500">Board Status:</span>{' '}
              <span className="font-medium">{item.board_license_status}</span>
            </div>
          )}
          <div className="bg-slate-50 p-3 rounded-lg">
            <span className="text-slate-500">LEIE Match:</span>{' '}
            <span className={`font-medium ${item.leie_match ? 'text-danger-600' : 'text-success-600'}`}>
              {item.leie_match ? 'Yes' : 'No'}
            </span>
          </div>
        </div>

        {/* Discrepancies */}
        {item.discrepancies && item.discrepancies.length > 0 && (
          <div className="mt-3 p-3 bg-danger-50 rounded-lg border border-danger-100">
            <p className="text-sm font-medium text-danger-800 mb-1">Discrepancies Found:</p>
            <ul className="list-disc list-inside text-sm text-danger-700">
              {item.discrepancies.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Reasoning */}
        {item.confidence_reasoning && (
          <div className="mt-3 p-3 bg-slate-50 rounded-lg">
            <p className="text-sm font-medium text-slate-700 mb-1">AI Reasoning:</p>
            <p className="text-sm text-slate-600">{item.confidence_reasoning}</p>
          </div>
        )}
      </div>

      {/* Source Links */}
      <div className="mt-4 flex gap-3 flex-wrap">
        <a
          href={`https://npiregistry.cms.hhs.gov/search?number=${item.npi_number}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          Look up on NPI Registry
        </a>
        <a
          href="https://search.dca.ca.gov/?BD=800"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          Search CA DCA
        </a>
        <a
          href="https://oig.hhs.gov/exclusions/exclusions_list.asp"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          Check LEIE List
        </a>
      </div>

      {/* Success/Error Messages */}
      {submitSuccess && (
        <div className="mt-4 p-3 bg-success-50 border border-success-200 rounded-lg text-success-700 text-sm">
          {submitSuccess}
        </div>
      )}
      {submitError && (
        <div className="mt-4 p-3 bg-danger-50 border border-danger-200 rounded-lg text-danger-700 text-sm">
          {submitError}
        </div>
      )}

      {/* Notes Input */}
      <div className="mt-4">
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Review Notes
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Enter notes about your review decision..."
          className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none h-20"
          disabled={isSubmitting || !!submitSuccess}
        />
      </div>

      {/* Action Buttons */}
      <div className="mt-4 flex gap-3">
        <button
          onClick={() => handleDecision('approved')}
          disabled={isSubmitting || !!submitSuccess}
          className="flex-1 bg-success-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-success-700 disabled:opacity-50 transition-colors"
        >
          {isSubmitting ? 'Submitting...' : 'Approve'}
        </button>
        <button
          onClick={() => handleDecision('rejected')}
          disabled={isSubmitting || !!submitSuccess}
          className="flex-1 bg-danger-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-danger-700 disabled:opacity-50 transition-colors"
        >
          Reject
        </button>
        <button
          onClick={() => handleDecision('needs_info')}
          disabled={isSubmitting || !!submitSuccess}
          className="flex-1 bg-warning-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-warning-700 disabled:opacity-50 transition-colors"
        >
          Request Info
        </button>
      </div>
    </div>
  );
}
