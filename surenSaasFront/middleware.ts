import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Vérifier si on est sur une route protégée
  if (request.nextUrl.pathname.startsWith('/dashboard')) {
    const sessionCookie = request.cookies.get('session_token')
    
    if (!sessionCookie) {
      // Logger l'absence de cookie
      console.log(`🔴 [Middleware] Cookie 'session_token' manquant pour ${request.nextUrl.pathname}`)
      console.log(`🔴 [Middleware] Redirection vers /login`)
      
      // Rediriger vers la page de login
      const loginUrl = new URL('/login', request.url)
      loginUrl.searchParams.set('redirect', request.nextUrl.pathname)
      loginUrl.searchParams.set('error', 'session_expired')
      return NextResponse.redirect(loginUrl)
    }
    
    // Cookie présent, logger pour debug
    console.log(`✅ [Middleware] Cookie présent pour ${request.nextUrl.pathname}`)
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*']
}
