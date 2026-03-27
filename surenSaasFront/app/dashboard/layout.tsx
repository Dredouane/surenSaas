'use client';

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/app/contexts/AuthContext";
import {
  Building2,
  Home,
  FileText,
  Users,
  Settings,
  Menu,
  ChevronDown,
  LogOut,
} from "lucide-react";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const getNavigation = (isAdmin: boolean) => [
  { name: "Accueil", href: "/dashboard", icon: Home },
  { name: "Factures", href: "/dashboard/invoices", icon: FileText },
  { name: "Clients", href: "/dashboard/clients", icon: Users },
  { name: "Paramètres", href: "/dashboard/settings", icon: Settings },
  ...(isAdmin ? [{ name: "Administration", href: "/dashboard/settings/admin/users", icon: Settings }] : []),
];

// Fonction pour obtenir les initiales de l'email
function getInitials(email: string): string {
  if (!email) return "??";
  const parts = email.split('@')[0].split(/[._-]/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return email.substring(0, 2).toUpperCase();
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const { user, loading } = useAuth();

  const userInitials = user ? getInitials(user.email) : "??";
  const orgSlug = user?.org_slug || 'suren';
  const orgName = user?.org_name || 'Mon Organisation';
  const isAdmin = user?.role === 'admin';
  const navigation = getNavigation(isAdmin);

  return (
    <div className="min-h-screen bg-background">
      {/* Header Mobile */}
      <header className="lg:hidden border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="flex items-center justify-between px-4 h-14">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600" />
            <span className="font-bold">SurenSaaS</span>
          </div>
          <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <SheetTrigger>
              <Button variant="ghost" size="icon" type="button">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              <MobileSidebar 
                orgName={orgName}
                orgSlug={orgSlug}
                pathname={pathname}
                user={user}
                loading={loading}
                isAdmin={isAdmin}
                onNavigate={() => setMobileMenuOpen(false)}
              />
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar Desktop */}
        <aside className="hidden lg:flex flex-col w-64 border-r bg-muted/10 h-screen sticky top-0">
          <div className="p-4 border-b">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600" />
              <span className="font-bold text-lg">SurenSaaS</span>
            </div>
          </div>

          <div className="p-4">
            <div className="flex items-center gap-2 p-2 rounded-lg border bg-card">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">{orgName}</span>
              <span className="text-xs text-muted-foreground ml-auto">({orgSlug})</span>
            </div>
          </div>

          <nav className="flex-1 px-3 py-2 space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
              const Icon = item.icon;
              
              return (
                <Link key={item.name} href={item.href}>
                  <Button
                    variant={isActive ? "secondary" : "ghost"}
                    className="w-full justify-start gap-3"
                  >
                    <Icon className="h-4 w-4" />
                    {item.name}
                  </Button>
                </Link>
              );
            })}
          </nav>

          <div className="p-4 border-t">
            {loading ? (
              <div className="flex items-center gap-3 mb-4">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-32" />
                </div>
              </div>
            ) : user ? (
              <div className="flex items-center gap-3 mb-4">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-gradient-to-br from-blue-600 to-violet-600 text-white text-xs">
                    {userInitials}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.email}</p>
                  <p className="text-xs text-muted-foreground truncate capitalize">{user.role}</p>
                </div>
              </div>
            ) : null}
            <Link href="/login">
              <Button variant="outline" className="w-full gap-2" size="sm">
                <LogOut className="h-4 w-4" />
                Déconnexion
              </Button>
            </Link>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-h-[calc(100vh-3.5rem)] lg:min-h-screen">
          {children}
        </main>
      </div>
    </div>
  );
}

function MobileSidebar({ 
  orgName,
  orgSlug,
  pathname,
  user,
  loading,
  isAdmin,
  onNavigate 
}: { 
  orgName: string;
  orgSlug: string;
  pathname: string;
  user: any;
  loading: boolean;
  isAdmin: boolean;
  onNavigate: () => void;
}) {
  const userInitials = user ? getInitials(user.email) : "??";
  const navigation = getNavigation(isAdmin);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600" />
          <span className="font-bold text-lg">SurenSaaS</span>
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center gap-2 p-2 rounded-lg border bg-card">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">{orgName}</span>
          <span className="text-xs text-muted-foreground ml-auto">({orgSlug})</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-2 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          
          return (
            <Link key={item.name} href={item.href} onClick={onNavigate}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className="w-full justify-start gap-3"
              >
                <Icon className="h-4 w-4" />
                {item.name}
              </Button>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t">
        {loading ? (
          <div className="flex items-center gap-3 mb-4">
            <Skeleton className="h-8 w-8 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
        ) : user ? (
          <div className="flex items-center gap-3 mb-4">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-gradient-to-br from-blue-600 to-violet-600 text-white text-xs">
                {userInitials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user.email}</p>
              <p className="text-xs text-muted-foreground truncate capitalize">{user.role}</p>
            </div>
          </div>
        ) : null}
        <Link href="/login">
          <Button variant="outline" className="w-full gap-2" size="sm">
            <LogOut className="h-4 w-4" />
            Déconnexion
          </Button>
        </Link>
      </div>
    </div>
  );
}
