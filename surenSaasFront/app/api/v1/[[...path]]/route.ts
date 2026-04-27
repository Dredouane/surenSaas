// app/api/v1/[[...path]]/route.ts
// Proxy toutes les requêtes /api/v1/* vers le backend

import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_URL || 'http://localhost:8080';

export async function GET(request: NextRequest) {
  return handleProxy(request, 'GET');
}

export async function POST(request: NextRequest) {
  return handleProxy(request, 'POST');
}

export async function PUT(request: NextRequest) {
  return handleProxy(request, 'PUT');
}

export async function DELETE(request: NextRequest) {
  return handleProxy(request, 'DELETE');
}

export async function PATCH(request: NextRequest) {
  return handleProxy(request, 'PATCH');
}

async function handleProxy(request: NextRequest, method: string) {
  // Extraire le chemin après /api/v1/
  const pathname = request.nextUrl.pathname;
  const pathMatch = pathname.match(/^\/api\/v1\/(.*)$/);
  const path = pathMatch ? pathMatch[1] : '';
  
  // Récupérer les query parameters
  const searchParams = request.nextUrl.search;
  const targetUrl = `${API_BASE_URL}/api/v1/${path}${searchParams}`;
  
  console.log(`🔄 Proxy ${method} ${pathname} → ${targetUrl}`);
  console.log(`   API_URL config: ${API_BASE_URL}`);
  
  try {
    // Détecter le content-type de la requête
    const contentType = request.headers.get('content-type') || '';
    const isMultipart = contentType.includes('multipart/form-data');
    const isFormUrlEncoded = contentType.includes('application/x-www-form-urlencoded');
    
    // Préparer les headers
    const headers: Record<string, string> = {};
    
    // Ne pas définir Content-Type pour multipart (le browser le fait avec le boundary)
    if (!isMultipart && !isFormUrlEncoded) {
      headers['Content-Type'] = 'application/json';
    }
    
    // Copier les headers importants
    const authHeader = request.headers.get('authorization');
    if (authHeader) {
      headers['authorization'] = authHeader;
    }
    
    const cookieHeader = request.headers.get('cookie');
    if (cookieHeader) {
      headers['cookie'] = cookieHeader;
    }
    
    // Récupérer le body si présent
    let body: string | FormData | undefined;
    
    if (method !== 'GET' && method !== 'HEAD') {
      if (isMultipart || isFormUrlEncoded) {
        // Pour les uploads de fichiers ou formulaires, forward le FormData tel quel
        body = await request.formData();
        console.log(`   Body: FormData (${isMultipart ? 'multipart' : 'form-urlencoded'})`);
      } else {
        // Pour les requêtes JSON, lire comme texte
        body = await request.text();
        // Masquer les champs sensibles dans les logs
        let logBody = body;
        try {
          const bodyObj = JSON.parse(body);
          if (bodyObj.password) {
            bodyObj.password = '***MASQUÉ***';
            logBody = JSON.stringify(bodyObj);
          }
        } catch {
          // Si pas JSON, on log tel quel mais tronqué
        }
        console.log(`   Body: ${logBody.substring(0, 200)}...`);
      }
    }
    
    console.log(`   → Envoi vers backend...`);
    
    // Faire la requête vers le backend
    const response = await fetch(targetUrl, {
      method,
      headers,
      body: body || undefined,
      cache: 'no-store',
    });
    
    console.log(`   ← Réponse: ${response.status} ${response.statusText}`);
    
    // Vérifier si c'est une erreur d'authentification avec redirection
    const authRedirect = response.headers.get('X-Auth-Redirect');
    const authError = response.headers.get('X-Auth-Error');
    
    if (response.status === 401) {
      if (authRedirect) {
        console.error(`   🔴 ERREUR: Cookie de session invalide ou expiré (${authError || 'unknown'})`);
        console.error(`   🔴 Redirection vers ${authRedirect} requise`);
        // Rediriger vers la page de login
        // Utiliser l'URL publique du frontend si disponible
        const frontendUrl = process.env.FRONTEND_URL;
        if (frontendUrl) {
          console.error(`   🔴 Utilisation de l'URL frontend: ${frontendUrl}`);
          return NextResponse.redirect(new URL(authRedirect, frontendUrl));
        } else {
          return NextResponse.redirect(new URL(authRedirect, request.url));
        }
      } else {
        console.error(`   🔴 ERREUR 401: Session invalide mais pas de header X-Auth-Redirect`);
        // Rediriger quand même vers /login pour les endpoints qui nécessitent une authentification
        // Sauf pour les endpoints publics comme /auth/*
        const pathname = request.nextUrl.pathname;
        if (!pathname.includes('/auth/')) {
          console.error(`   🔴 Redirection vers /login pour ${pathname}`);
          const frontendUrl = process.env.FRONTEND_URL;
          if (frontendUrl) {
            return NextResponse.redirect(new URL('/login', frontendUrl));
          } else {
            return NextResponse.redirect(new URL('/login', request.url));
          }
        }
      }
    }
    
    // Récupérer le body de réponse
    const responseBody = await response.text();
    
    if (!response.ok) {
      console.error(`   ❌ Backend error: ${response.status} - ${responseBody.substring(0, 200)}`);
    }
    
    // Créer la réponse
    const nextResponse = new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
    });
    
    // Copier les headers de réponse (sauf ceux qui posent problème)
    response.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase();
      if (!['content-encoding', 'transfer-encoding', 'content-length'].includes(lowerKey)) {
        nextResponse.headers.set(key, value);
      }
    });
    
    return nextResponse;
    
  } catch (error) {
    console.error('❌ Proxy error:', error);
    return NextResponse.json(
      { 
        error: 'Backend unavailable', 
        details: String(error),
        targetUrl,
        apiUrl: API_BASE_URL 
      },
      { status: 503 }
    );
  }
}
