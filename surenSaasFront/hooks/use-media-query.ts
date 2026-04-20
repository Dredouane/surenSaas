"use client";

import { useState, useEffect } from "react";

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    
    // Set initial value
    setMatches(media.matches);

    // Create event listener
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    
    // Add listener
    media.addEventListener("change", listener);

    // Cleanup
    return () => media.removeEventListener("change", listener);
  }, [query]);

  return matches;
}

// Hook prédéfini pour mobile (< 768px)
export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 767px)");
}

// Hook prédéfini pour tablet (768px - 1023px)
export function useIsTablet(): boolean {
  return useMediaQuery("(min-width: 768px) and (max-width: 1023px)");
}

// Hook prédéfini pour desktop (>= 1024px)
export function useIsDesktop(): boolean {
  return useMediaQuery("(min-width: 1024px)");
}
