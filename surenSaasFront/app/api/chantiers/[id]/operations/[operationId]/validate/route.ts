import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export async function POST(request: NextRequest, { params }: { params: { id: string; operationId: string } }) {
  const orgId = request.nextUrl.searchParams.get('org_id');
  if (!orgId) return NextResponse.json({ success: false, error: 'org_id required' }, { status: 400 });
  try {
    const body = await request.json();
    const res = await fetch(`${API_BASE}/api/v1/chantiers/${params.id}/operations/${params.operationId}?org_id=${orgId}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    return NextResponse.json({ success: true, data: await res.json() });
  } catch (error) {
    return NextResponse.json({ success: false, error: 'Proxy error' }, { status: 502 });
  }
}
