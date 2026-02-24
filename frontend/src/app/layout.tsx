import type { Metadata } from 'next';
import './globals.css';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'EverCred POC',
  description: 'Physician Credentialing Verification Agent',
};

const tabs = [
  { name: 'Verify', href: '/verify' },
  { name: 'Batch', href: '/batch' },
  { name: 'Dashboard', href: '/dashboard' },
  { name: 'HITL Queue', href: '/review' },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              {/* Logo/Brand */}
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">EC</span>
                </div>
                <h1 className="text-xl font-semibold text-slate-800">
                  EverCred POC
                </h1>
              </div>

              {/* Navigation Tabs */}
              <nav className="flex space-x-1">
                {tabs.map((tab) => (
                  <Link
                    key={tab.name}
                    href={tab.href}
                    className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-primary-600 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    {tab.name}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
