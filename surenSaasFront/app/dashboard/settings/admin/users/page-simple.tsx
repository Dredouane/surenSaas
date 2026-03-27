'use client';

import { useState, useEffect } from "react";

export default function AdminUsersPage() {
  console.log('🔥 SIMPLE ADMIN RENDER');
  
  const [data, setData] = useState<string>("Chargement...");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    console.log('⚡ useEffect triggered');
    
    const fetchData = async () => {
      try {
        console.log('📡 Fetching...');
        const response = await fetch('/api/v1/admin/pre-authorized-emails', {
          credentials: 'include'
        });
        
        console.log('📥 Response:', response.status);
        
        if (response.ok) {
          const json = await response.json();
          setData(`Trouvé ${json.length} utilisateurs`);
        } else {
          setError(`Erreur ${response.status}`);
        }
      } catch (err) {
        console.error('❌ Error:', err);
        setError(err instanceof Error ? err.message : 'Erreur');
      }
    };
    
    fetchData();
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      <h1>Administration (Test)</h1>
      <p>Status: {error || data}</p>
      <button onClick={() => window.location.reload()}>
        Rafraîchir
      </button>
    </div>
  );
}
