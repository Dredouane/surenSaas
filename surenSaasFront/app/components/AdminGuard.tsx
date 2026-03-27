'use client';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/app/contexts/AuthContext";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Loader2 } from "lucide-react";

interface AdminGuardProps {
  children: React.ReactNode;
}

export default function AdminGuard({ children }: AdminGuardProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  console.log('🔒 AdminGuard RENDER:', { loading, user: user?.email, role: user?.role });

  useEffect(() => {
    console.log('🔒 AdminGuard useEffect:', { loading, hasUser: !!user, role: user?.role });
    if (!loading) {
      if (!user) {
        console.log('🚫 No user, redirecting...');
        router.push('/dashboard');
      } else if (user.role !== 'admin') {
        console.log('🚫 Not admin, redirecting...');
        router.push('/dashboard');
      } else {
        console.log('✅ Admin access granted');
      }
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user || user.role !== 'admin') {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Accès réservé aux administrateurs. Vous allez être redirigé...
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return <>{children}</>;
}
