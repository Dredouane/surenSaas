/**
 * Helper fetch pour les appels API de la TMA.
 * Ajoute automatiquement org_id, Authorization, X-Correlation-ID.
 */

let _correlationId = '';
let _jwt = '';
let _orgId = '';

export function initTmaFetch(jwt: string, orgId: string, correlationId: string) {
  _jwt = jwt;
  _orgId = orgId;
  _correlationId = correlationId;
}

export async function tmaFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const separator = path.includes('?') ? '&' : '?';
  const url = `${path}${separator}org_id=${_orgId}`;

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (_jwt) {
    headers['Authorization'] = `Bearer ${_jwt}`;
  }

  if (_correlationId) {
    headers['X-Correlation-ID'] = _correlationId;
  }

  return fetch(url, { ...options, headers });
}

export async function tmaExtract(text: string, workflow: string): Promise<any> {
  const res = await tmaFetch('/api/v1/tma/extract', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, workflow }),
  });
  if (!res.ok) return null;
  return res.json();
}
