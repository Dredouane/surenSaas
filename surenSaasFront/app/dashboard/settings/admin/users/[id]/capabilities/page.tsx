'use client';

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/app/contexts/AuthContext";
import { 
  ArrowLeft, 
  Shield, 
  User,
  Save,
  AlertCircle,
  CheckCircle,
  Loader2,
  Building2,
  FileText,
  Users,
  Settings,
  Lock
} from "lucide-react";

interface Capability {
  capability_code: string;
  resource: string;
  action: string;
  description: string;
}

interface UserCapability {
  capability_code: string;
  resource: string;
  action: string;
}

interface UserInfo {
  id: string;
  email: string;
  role: string;
}

const RESOURCE_ICONS: Record<string, React.ReactNode> = {
  construction: <Building2 className="h-5 w-5" />,
  invoices: <FileText className="h-5 w-5" />,
  clients: <Users className="h-5 w-5" />,
  settings: <Settings className="h-5 w-5" />,
  admin: <Shield className="h-5 w-5" />,
};

const RESOURCE_NAMES: Record<string, string> = {
  construction: "Construction",
  invoices: "Factures",
  clients: "Clients",
  settings: "Paramètres",
  admin: "Administration",
};

const ACTION_LABELS: Record<string, string> = {
  read: "Lecture",
  write: "Écriture",
};

export default function UserCapabilitiesPage() {
  const router = useRouter();
  const params = useParams();
  const { user: currentUser } = useAuth();
  const userId = params.id as string;
  
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [allCapabilities, setAllCapabilities] = useState<Capability[]>([]);
  const [userCapabilities, setUserCapabilities] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetchData();
  }, [userId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Récupérer les capabilities disponibles pour l'org
      const capsResponse = await fetch('/api/v1/admin/organization-capabilities', {
        credentials: 'include'
      });
      
      if (!capsResponse.ok) throw new Error('Erreur chargement capabilities');
      const capsData = await capsResponse.json();
      setAllCapabilities(capsData.capabilities || []);
      
      // Récupérer les capabilities de l'utilisateur
      const userCapsResponse = await fetch(`/api/v1/admin/users/${userId}/capabilities`, {
        credentials: 'include'
      });
      
      if (!userCapsResponse.ok) throw new Error('Erreur chargement user capabilities');
      const userCapsData = await userCapsResponse.json();
      setUserCapabilities(userCapsData.capabilities?.map((c: UserCapability) => c.capability_code) || []);
      
      // TODO: Récupérer les infos de l'utilisateur
      setUserInfo({
        id: userId,
        email: "utilisateur@exemple.com", // À remplacer par l'API
        role: "user"
      });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleCapability = (capCode: string) => {
    setUserCapabilities(prev => {
      if (prev.includes(capCode)) {
        return prev.filter(c => c !== capCode);
      } else {
        return [...prev, capCode];
      }
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`/api/v1/admin/users/${userId}/capabilities`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ capabilities: userCapabilities })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Erreur lors de la sauvegarde');
      }

      setSuccess('Les permissions ont été mises à jour avec succès');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setSaving(false);
    }
  };

  // Grouper les capabilities par resource
  const groupedCapabilities = allCapabilities.reduce((acc, cap) => {
    if (!acc[cap.resource]) {
      acc[cap.resource] = [];
    }
    acc[cap.resource].push(cap);
    return acc;
  }, {} as Record<string, Capability[]>);

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Button variant="ghost" size="icon" onClick={() => router.push('/dashboard/settings/admin/users')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Gestion des droits</h1>
          <p className="text-muted-foreground">
            Définissez les permissions granulaires pour {userInfo?.email}
          </p>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="mb-6 bg-green-50 border-green-200">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* Info utilisateur */}
      <Card className="mb-6">
        <CardContent className="py-4">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center text-white font-bold">
              {userInfo?.email.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="font-medium">{userInfo?.email}</p>
              <Badge variant={userInfo?.role === 'admin' ? 'default' : 'secondary'}>
                {userInfo?.role === 'admin' ? 'Administrateur' : 'Utilisateur'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Capabilities par resource */}
      <div className="space-y-6">
        {Object.entries(groupedCapabilities).map(([resource, capabilities]) => (
          <Card key={resource}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                {RESOURCE_ICONS[resource] || <Lock className="h-5 w-5" />}
                {RESOURCE_NAMES[resource] || resource}
              </CardTitle>
              <CardDescription>
                Permissions pour le module {RESOURCE_NAMES[resource] || resource}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                {capabilities.map((cap) => (
                  <div 
                    key={cap.capability_code}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="space-y-1">
                      <Label htmlFor={cap.capability_code} className="font-medium cursor-pointer">
                        {ACTION_LABELS[cap.action] || cap.action}
                      </Label>
                      {cap.description && (
                        <p className="text-sm text-muted-foreground">{cap.description}</p>
                      )}
                    </div>
                    <Switch
                      id={cap.capability_code}
                      checked={userCapabilities.includes(cap.capability_code)}
                      onCheckedChange={() => handleToggleCapability(cap.capability_code)}
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}

        {Object.keys(groupedCapabilities).length === 0 && (
          <Card>
            <CardContent className="py-12 text-center">
              <Lock className="h-12 w-12 mx-auto mb-3 text-muted-foreground opacity-50" />
              <p className="text-muted-foreground">Aucune capability définie pour cette organisation</p>
              <p className="text-sm text-muted-foreground mt-1">
                Contactez l'administrateur système pour configurer les permissions
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Bouton de sauvegarde */}
      <div className="mt-8 flex justify-end gap-4">
        <Button variant="outline" onClick={() => router.push('/dashboard/settings/admin/users')}>
          Annuler
        </Button>
        <Button 
          onClick={handleSave}
          disabled={saving}
          className="bg-gradient-to-r from-blue-600 to-violet-600"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Sauvegarde...
            </>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              Enregistrer les modifications
            </>
          )}
        </Button>
      </div>

      {/* Résumé */}
      {userCapabilities.length > 0 && (
        <Card className="mt-6 bg-muted/50">
          <CardHeader>
            <CardTitle className="text-base">Permissions actuelles</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {userCapabilities.map(capCode => (
                <Badge key={capCode} variant="secondary" className="text-xs">
                  {capCode}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
