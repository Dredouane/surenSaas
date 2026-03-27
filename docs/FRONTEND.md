# Frontend (Next.js 14)

## Stack
- **Framework** : Next.js 14 App Router
- **Langage** : TypeScript strict
- **Styling** : Tailwind CSS + shadcn/ui
- **Auth** : Supabase Auth (email + password)

## Structure routing
```
app/
├── [org]/                    # Multi-tenancy par slug org
│   ├── (dashboard)/          # Layout protégé
│   ├── login/                # Auth magic link + password
│   └── page.tsx              # Landing org
├── api/                      # Routes API internes
└── layout.tsx               # Root avec providers
```

## Configuration critique

### next.config.js
```javascript
{
  images: { unoptimized: true },  // Cloud Run
  output: 'standalone',            // Docker optimisé
  env: {
    BUILD_ID: process.env.BUILD_ID // Pour force-reload
  }
}
```

### Theme dynamique
- CSS variables par organisation (stocké en base)
- Injection dans `<head>` via middleware
- Fallback sur thème par défaut

### Version force-reload
- Middleware lit BUILD_ID via headers
- Comparaison avec `/api/build-info`
- Hard reload si mismatch

## Auth Flow

### Page `/[org]/login`
```tsx
// 1. EmailInput + bouton "Continuer"
// 2. POST /api/v1/auth/check-email
// 3. Affiche formulaire adapté :
//    - Nouveau : CreatePasswordForm
//    - Existant : LoginForm
// 4. Soumission → Supabase Auth
// 5. Succès → redirect /[org]/dashboard
```

### Composants auth
- `EmailStep` : Input email + validation
- `PasswordStep` : Input password (création ou login)
- `AuthForm` : Orchestrateur avec étapes

### Dépendances clés
```json
{
  "next": "^14",
  "@supabase/supabase-js": "^2",
  "tailwindcss": "^3",
  "shadcn-ui": "latest"
}
```

## Exemple LoginPage
```tsx
// app/[org]/login/page.tsx
'use client';
import { useState } from 'react';
import { useParams } from 'next/navigation';

export default function LoginPage() {
  const { org } = useParams();
  const [step, setStep] = useState<'email' | 'password'>('email');
  const [email, setEmail] = useState('');
  const [isNewUser, setIsNewUser] = useState(false);

  const checkEmail = async (email: string) => {
    const res = await fetch(`/api/v1/auth/check-email`, {
      method: 'POST',
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    
    if (!data.authorized) {
      alert('Contactez votre administrateur');
      return;
    }
    
    setIsNewUser(!data.exists);
    setStep('password');
  };

  // ... render selon étape
}
```

## Middleware auth
```typescript
// middleware.ts
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const org = pathname.split('/')[1];
  
  // Vérifier session Supabase
  // Si pas de session et pas sur /login → redirect /[org]/login
  // Vérifier org_id dans session match l'URL
}
```

## Scripts utiles
```bash
# Développement
npm run dev                    # Local sur :3000

# Build test
npm run build                  # Vérifier build_id injecté

# Docker local
docker-compose up frontend     # Test iso-prod
```

## Points de vigilance
- Toujours utiliser `unoptimized: true` pour images
- Ne jamais hardcoder l'URL API (variable env)
- Vérifier org_id match le slug URL dans middleware
- Rate limiting côté client (désactiver bouton après clic)
