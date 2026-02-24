import { redirect } from 'next/navigation';

export default function Home() {
  // Redirect to Verify tab as the default view
  redirect('/verify');
}
