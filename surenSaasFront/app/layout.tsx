import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";
import { AuthProvider } from "./contexts/AuthContext";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata = {
  title: "SurenSaaS",
  description: "SaaS multi-PME pour construction, nettoyage et diagnostic énergétique",
  icons: {
    icon: '/favicon.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className={cn("font-sans", inter.variable)}>
      <body className="min-h-screen bg-background">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
