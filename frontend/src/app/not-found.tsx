import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-slate-300">404</h1>
        <h2 className="mt-4 text-2xl font-semibold text-slate-800">
          Page Not Found
        </h2>
        <p className="mt-2 text-slate-600">
          The page you're looking for doesn't exist.
        </p>
        <Link
          href="/verify"
          className="mt-6 inline-block px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
        >
          Go to Verify
        </Link>
      </div>
    </div>
  );
}
