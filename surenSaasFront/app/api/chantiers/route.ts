import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const orgId = searchParams.get('org_id');
  if (!orgId) return NextResponse.json({ success: false, error: 'org_id required' }, { status: 400 });
  try {
    const res = await fetch(`${API_BASE}/api/v1/chantiers?org_id=${orgId}`, { credentials: 'include' });
    const data = await res.json();
    return NextResponse.json({ success: true, data });
  } catch (error) {
    return NextResponse.json({ success: false, error: 'Proxy error' }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const orgId = searchParams.get('org_id');
  if (!orgId) return NextResponse.json({ success: false, error: 'org_id required' }, { status: 400 });
  try {
    const body = await request.json();
    const res = await fetch(`${API_BASE}/api/v1/chantiers?org_id=${orgId}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json({ success: true, data }, { status: res.status });
  } catch (error) {
    return NextResponse.json({ success: false, error: 'Proxy error' }, { status: 502 });
  }
}
