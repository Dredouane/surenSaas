# Frontend (Next.js 14)

## Stack
- **Framework**: Next.js 14 App Router
- **Language**: Strict TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **Auth**: Supabase Auth (email + password)

## Routing structure
```
app/
├── [org]/                    # Multi-tenancy by org slug
│   ├── (dashboard)/          # Protected layout
│   ├── login/                # Auth magic link + password
│   └── page.tsx              # Org landing
├── api/                      # Internal API routes
└── layout.tsx               # Root with providers
```

## Critical configuration

### next.config.js
```javascript
{
  images: { unoptimized: true },  // Cloud Run
  output: 'standalone',            // Optimized Docker
  env: {
    BUILD_ID: process.env.BUILD_ID // For force-reload
  }
}
```

### Dynamic theme
- CSS variables per organization (stored in database)
- Injection into `<head>` via middleware
- Fallback to default theme

### Force-reload version
- Middleware reads BUILD_ID via headers
- Comparison with `/api/build-info`
- Hard reload if mismatch

## Auth Flow

### Page `/[org]/login`
```tsx
// 1. EmailInput + "Continue" button
// 2. POST /api/v1/auth/check-email
// 3. Displays the appropriate form:
//    - New: CreatePasswordForm
//    - Existing: LoginForm
// 4. Submission → Supabase Auth
// 5. Success → redirect /[org]/dashboard
```

### Auth components
- `EmailStep`: Email input + validation
- `PasswordStep`: Password input (creation or login)
- `AuthForm`: Orchestrator with steps

### Key dependencies
```json
{
  "next": "^14",
  "@supabase/supabase-js": "^2",
  "tailwindcss": "^3",
  "shadcn-ui": "latest"
}
```

## LoginPage example
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
      alert('Contact your administrator');
      return;
    }
    
    setIsNewUser(!data.exists);
    setStep('password');
  };

  // ... render based on step
}
```

## Auth middleware
```typescript
// middleware.ts
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const org = pathname.split('/')[1];
  
  // Check Supabase session
  // If no session and not on /login → redirect /[org]/login
  // Verify org_id in session matches the URL
}
```

## Useful scripts
```bash
# Development
npm run dev                    # Local on :3000

# Build test
npm run build                  # Verify build_id injected

# Local Docker
docker-compose up frontend     # prod-identical test
```

## Points of caution
- Always use `unoptimized: true` for images
- Never hardcode the API URL (env variable)
- Verify that org_id matches the URL slug in the middleware
- Rate limiting on the client side (disable button after click)
