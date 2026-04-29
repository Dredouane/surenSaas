'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Eye, EyeOff, Building2 } from "lucide-react";

interface CheckEmailResponse {
  authorized: boolean;
  exists: boolean;
  org_id: string;
  org_slug: string;
  org_name: string;
  role: string;
  message?: string;
}

// Organisation fixe depuis les variables d'environnement
const ORG_SLUG = process.env.NEXT_PUBLIC_ORG_SLUG || 'suren';
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || '';
console.log('🔧 ORG_SLUG configuré:', ORG_SLUG);
console.log('🔧 ORG_ID configuré:', ORG_ID);

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setUser, refetch } = useAuth();
  
  const rawRedirect = searchParams.get('redirect');
  const [redirectUrl, setRedirectUrl] = useState<string>('/dashboard');
  
  useEffect(() => {
    // Sécuriser la redirection
    const safe = rawRedirect && rawRedirect.startsWith('/') 
      ? rawRedirect 
      : '/dashboard';
    setRedirectUrl(safe);
  }, [rawRedirect]);
  
  const [step, setStep] = useState<'email' | 'password'>('email');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isNewUser, setIsNewUser] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const checkEmail = async () => {
    setLoading(true);
    setError('');
    
    try {
      console.log('🔍 Vérification email:', email);
      const res = await fetch(`/api/v1/auth/check-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      
      const data: CheckEmailResponse = await res.json();
      console.log('📧 Réponse check-email:', data);
      
      if (!data.authorized) {
        setError(data.message || 'Contactez votre administrateur');
        return;
      }
      
      // Vérifier que l'email appartient bien à cette organisation
      // On vérifie soit par org_slug, soit par org_id si org_slug est vide
      const orgMatch = data.org_slug === ORG_SLUG || data.org_id === ORG_ID;
      if (!orgMatch) {
        setError(`Cet email n'est pas autorisé pour ${ORG_SLUG}`);
        return;
      }
      
      const isNew = !data.exists;
      console.log('👤 Utilisateur existe:', data.exists, '- Nouveau:', isNew);
      setIsNewUser(isNew);
      setStep('password');
    } catch (err) {
      console.error('❌ Erreur check-email:', err);
      setError('Erreur de connexion');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const endpoint = isNewUser ? '/api/v1/auth/signup' : '/api/v1/auth/login';
      const body = isNewUser 
        ? { email, password, org_id: ORG_ID }
        : { email, password };
      
      console.log('🚀 Envoi formulaire - isNewUser:', isNewUser, 'endpoint:', endpoint);
      
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'include',
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erreur de connexion');
      }
      
      const data = await res.json();
      
      // Recharger le profil utilisateur pour mettre à jour le contexte
      console.log('✅ Login réussi, rechargement du profil...');
      await refetch();
      
      // Attendre que le contexte soit à jour
      await new Promise(r => setTimeout(r, 500));
      
      router.push(redirectUrl);
      
    } catch (err: any) {
      setError(err.message || 'Erreur de connexion');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
      <Card className="w-full max-w-md border-2 shadow-lg">
        <CardHeader className="space-y-1">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600" />
            <span className="text-xl font-bold">SurenSaaS</span>
          </div>
          <CardTitle className="text-2xl">
            {step === 'email' ? 'Connexion' : isNewUser ? 'Créer votre compte' : 'Mot de passe'}
          </CardTitle>
          <CardDescription>
            {step === 'email' 
              ? 'Entrez votre email pour continuer'
              : isNewUser 
                ? 'Définissez votre mot de passe'
                : 'Entrez votre mot de passe'
            }
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Badge Organisation */}
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-muted-foreground" />
            <Badge variant="secondary" className="font-normal">
              {ORG_SLUG}
            </Badge>
          </div>

          <Separator />

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {step === 'email' ? (
            <form onSubmit={(e) => { e.preventDefault(); checkEmail(); }} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="vous@entreprise.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              
              <Button 
                type="submit" 
                className="w-full bg-gradient-to-r from-blue-600 to-violet-600"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Vérification...
                  </>
                ) : (
                  'Continuer'
                )}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="password">
                  {isNewUser ? 'Créer un mot de passe' : 'Votre mot de passe'}
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    minLength={8}
                    required
                    autoComplete={isNewUser ? 'new-password' : 'current-password'}
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>
                {isNewUser && (
                  <p className="text-xs text-muted-foreground">Minimum 8 caractères</p>
                )}
              </div>

              <Button 
                type="submit" 
                className="w-full bg-gradient-to-r from-blue-600 to-violet-600"
                disabled={loading || password.length < 8}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Connexion...
                  </>
                ) : (
                  isNewUser ? 'Créer mon compte' : 'Se connecter'
                )}
              </Button>

              {!isNewUser && (
                <Button
                  type="button"
                  variant="link"
                  className="w-full"
                  onClick={() => alert('Fonctionnalité à venir')}
                >
                  Mot de passe oublié ?
                </Button>
              )}

              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => {
                  setStep('email');
                  setPassword('');
                  setError('');
                }}
              >
                Retour
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}
