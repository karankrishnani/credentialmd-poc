'use client';

import { useState } from 'react';

export default function ReviewPage() {
  const [queue, setQueue] = useState<any[]>([]);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-semibold text-slate-800">
          HITL Review Queue
        </h2>
        <p className="mt-1 text-slate-600">
          Verifications requiring human review and decision
        </p>
      </div>

      {/* Queue */}
      {queue.length === 0 ? (
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
          {queue.map((item) => (
            <HITLCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function HITLCard({ item }: { item: any }) {
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleDecision = async (decision: 'approved' | 'rejected' | 'needs_info') => {
    setIsSubmitting(true);
    try {
      // TODO: Call API
      console.log('Decision:', decision, 'Notes:', notes);
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
        </div>
        <span className="px-3 py-1 text-sm font-medium text-escalated-700 bg-escalated-100 rounded-full">
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
        <p className="text-sm font-medium text-slate-700">Collected Evidence</p>
        <div className="mt-2 text-sm text-slate-600">
          {/* TODO: Show evidence summary */}
          <p>Evidence data will be displayed here.</p>
        </div>
      </div>

      {/* Source Links */}
      <div className="mt-4 flex gap-3">
        <a
          href={`https://npiregistry.cms.hhs.gov/search?number=${item.npi_number}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          Look up on NPI Registry →
        </a>
        <a
          href="https://search.dca.ca.gov/?BD=800"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          Search CA DCA →
        </a>
      </div>

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
          disabled={isSubmitting}
        />
      </div>

      {/* Action Buttons */}
      <div className="mt-4 flex gap-3">
        <button
          onClick={() => handleDecision('approved')}
          disabled={isSubmitting}
          className="flex-1 bg-success-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-success-700 disabled:opacity-50"
        >
          Approve
        </button>
        <button
          onClick={() => handleDecision('rejected')}
          disabled={isSubmitting}
          className="flex-1 bg-danger-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-danger-700 disabled:opacity-50"
        >
          Reject
        </button>
        <button
          onClick={() => handleDecision('needs_info')}
          disabled={isSubmitting}
          className="flex-1 bg-warning-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-warning-700 disabled:opacity-50"
        >
          Request More Info
        </button>
      </div>
    </div>
  );
}
