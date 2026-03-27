import { redirect } from 'next/navigation';

export default function HomePage() {
  // Redirige vers la page de login
  redirect('/login');
}
