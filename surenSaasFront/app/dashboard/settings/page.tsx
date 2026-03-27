'use client';

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/app/contexts/AuthContext";
import { 
  Building2, 
  User, 
  Bell, 
  Shield, 
  Users, 
  ChevronRight,
  AlertCircle,
  Lock
} from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const isAdmin = user?.role === 'admin';

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Paramètres</h1>
        <p className="text-muted-foreground mt-1">
          Gérez les paramètres de votre compte et de votre organisation
        </p>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-flex">
          <TabsTrigger value="general">Général</TabsTrigger>
          <TabsTrigger value="profile">Profil</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          {isAdmin && (
            <TabsTrigger value="admin" className="bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300">
              <Shield className="h-4 w-4 mr-2" />
              Admin
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Informations de l'organisation
              </CardTitle>
              <CardDescription>
                Modifiez les informations de votre organisation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Nom de l'organisation</label>
                  <input 
                    type="text" 
                    className="w-full px-3 py-2 border rounded-md bg-background"
                    defaultValue={user?.org_name || "Mon Organisation"}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Slug</label>
                  <input 
                    type="text" 
                    className="w-full px-3 py-2 border rounded-md bg-muted"
                    defaultValue={user?.org_slug || "org"}
                    disabled
                  />
                  <p className="text-xs text-muted-foreground">
                    Le slug ne peut pas être modifié
                  </p>
                </div>
              </div>
              <Button>Enregistrer les modifications</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Préférences</CardTitle>
              <CardDescription>
                Personnalisez votre expérience
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Notifications email</p>
                  <p className="text-sm text-muted-foreground">
                    Recevoir les notifications par email
                  </p>
                </div>
                <input type="checkbox" className="rounded" defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Mode sombre</p>
                  <p className="text-sm text-muted-foreground">
                    Activer le thème sombre
                  </p>
                </div>
                <input type="checkbox" className="rounded" />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="profile" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Profil utilisateur
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Email</label>
                <input 
                  type="email" 
                  className="w-full px-3 py-2 border rounded-md bg-muted"
                  defaultValue={user?.email}
                  disabled
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Rôle</label>
                <input 
                  type="text" 
                  className="w-full px-3 py-2 border rounded-md bg-muted capitalize"
                  defaultValue={user?.role}
                  disabled
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Paramètres de notification
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-muted-foreground">
                Les paramètres de notification seront disponibles prochainement.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {isAdmin && (
          <TabsContent value="admin" className="space-y-6">
            <Card className="border-amber-200 dark:border-amber-800">
              <CardHeader className="bg-amber-50/50 dark:bg-amber-900/10">
                <CardTitle className="flex items-center gap-2 text-amber-700 dark:text-amber-300">
                  <Shield className="h-5 w-5" />
                  Paramètres avancés - Administration
                </CardTitle>
                <CardDescription>
                  Gestion des utilisateurs et des permissions (accès réservé aux administrateurs)
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 pt-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <Card className="cursor-pointer hover:border-amber-300 transition-colors" onClick={() => router.push('/dashboard/settings/admin/users')}>
                    <CardHeader className="pb-3">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Users className="h-5 w-5 text-amber-600" />
                        Utilisateurs autorisés
                      </CardTitle>
                      <CardDescription className="text-sm">
                        Gérer les emails autorisés à rejoindre l'organisation
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center text-sm text-amber-600">
                        <span>Gérer les accès</span>
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="cursor-pointer hover:border-amber-300 transition-colors" onClick={() => router.push('/dashboard/settings/admin/capabilities')}>
                    <CardHeader className="pb-3">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Lock className="h-5 w-5 text-amber-600" />
                        Gestion des droits
                      </CardTitle>
                      <CardDescription className="text-sm">
                        Définir les permissions granulaires par utilisateur
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center text-sm text-amber-600">
                        <span>Gérer les permissions</span>
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <div className="mt-4 p-4 bg-muted rounded-lg">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
                    <div>
                      <p className="font-medium text-sm">Zone restreinte</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Ces fonctionnalités permettent de contrôler qui peut accéder à l'application 
                        et quelles actions ils peuvent effectuer. Utilisez-les avec précaution.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
