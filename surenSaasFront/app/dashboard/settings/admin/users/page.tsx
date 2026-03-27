'use client';

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TelegramInvitationDialog } from "@/components/telegram/invitation-dialog";
import { useAuth } from "@/app/contexts/AuthContext";
import { 
  ArrowLeft, 
  Plus, 
  Trash2, 
  Shield, 
  User,
  Mail,
  AlertCircle,
  CheckCircle,
  XCircle,
  Settings,
  Loader2,
  MessageCircle
} from "lucide-react";

interface PreAuthorizedUser {
  id: string;                    // pre_authorized_emails.id
  user_id?: string;              // users.id (réel ID utilisateur, présent si used_at)
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  invited_at: string;
  used_at: string | null;
  invited_by: string | null;
  telegram_linked?: boolean;
}

export default function AdminUsersPage() {
  console.log('🔥 AdminUsersPage RENDER START');
  
  const router = useRouter();
  const { user } = useAuth();
  const [users, setUsers] = useState<PreAuthorizedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  
  // Formulaire d'ajout
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState("user");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Dialog invitation Telegram
  const [selectedUserForTelegram, setSelectedUserForTelegram] = useState<PreAuthorizedUser | null>(null);
  const [isTelegramDialogOpen, setIsTelegramDialogOpen] = useState(false);

  // Chargement immédiat au montage
  useEffect(() => {
    console.log('⚡ AdminUsersPage MOUNTED');
    console.log('👤 User from context:', user);
    
    // Charger immédiatement, même sans user (l'API vérifie la session)
    fetchUsers();
  }, []);  // Se déclenche une seule fois au montage

  const fetchUsers = useCallback(async () => {
    console.log('🚀 fetchUsers called');
    try {
      setLoading(true);
      console.log('📡 Calling /api/v1/admin/pre-authorized-emails');
      const response = await fetch('/api/v1/admin/pre-authorized-emails', {
        credentials: 'include'
      });
      
      console.log('📥 Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Response error:', errorText);
        throw new Error(`Erreur ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      console.log('✅ Data received:', data);
      console.log('🔍 First user data:', data[0]);
      console.log('🔍 First user user_id:', data[0]?.user_id);
      console.log('🔍 First user id:', data[0]?.id);
      setUsers(data);
    } catch (err) {
      console.error('❌ Error in fetchUsers:', err);
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail) return;

    setIsSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch('/api/v1/admin/pre-authorized-emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: newEmail, role: newRole })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Erreur lors de l\'ajout');
      }

      setSuccess(`L'email ${newEmail} a été ajouté avec succès`);
      setNewEmail("");
      setNewRole("user");
      setIsDialogOpen(false);
      fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (userId: string, currentStatus: boolean) => {
    try {
      const response = await fetch(`/api/v1/admin/pre-authorized-emails/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ is_active: !currentStatus })
      });

      if (!response.ok) throw new Error('Erreur lors de la mise à jour');
      
      fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cet email ?')) return;

    try {
      const response = await fetch(`/api/v1/admin/pre-authorized-emails/${userId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Erreur lors de la suppression');
      
      fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const openTelegramInvitation = (user: PreAuthorizedUser) => {
    console.log('🔔 Ouverture invitation Telegram pour:', user.email);
    console.log('🔔 user_id:', user.user_id);
    console.log('🔔 id (pre_authorized):', user.id);
    
    if (!user.user_id) {
      console.error('❌ Pas de user_id pour', user.email);
      setError(`L'utilisateur ${user.email} doit d'abord se connecter à l'application avant de pouvoir être invité sur Telegram.`);
      return;
    }
    
    setSelectedUserForTelegram(user);
    setIsTelegramDialogOpen(true);
  };

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Button variant="ghost" size="icon" onClick={() => router.push('/dashboard/settings')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">Utilisateurs autorisés</h1>
          <p className="text-muted-foreground">
            Gérez les emails autorisés à rejoindre votre organisation
          </p>
        </div>
        <Button onClick={fetchUsers} variant="outline" disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Rafraîchir'}
        </Button>
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

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Liste des utilisateurs */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Liste des utilisateurs</CardTitle>
              <CardDescription>
                {users.length} email{users.length > 1 ? 's' : ''} enregistré{users.length > 1 ? 's' : ''}
              </CardDescription>
            </div>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-gradient-to-r from-blue-600 to-violet-600">
                  <Plus className="h-4 w-4 mr-2" />
                  Ajouter
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Ajouter un utilisateur</DialogTitle>
                  <DialogDescription>
                    L'utilisateur pourra créer un compte avec cet email
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleAddUser}>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="email">Email</Label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="utilisateur@entreprise.com"
                        value={newEmail}
                        onChange={(e) => setNewEmail(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="role">Rôle initial</Label>
                      <Select value={newRole} onValueChange={setNewRole}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="user">Utilisateur</SelectItem>
                          <SelectItem value="admin">Administrateur</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                      Annuler
                    </Button>
                    <Button 
                      type="submit" 
                      className="bg-gradient-to-r from-blue-600 to-violet-600"
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Ajout...
                        </>
                      ) : (
                        'Ajouter'
                      )}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : users.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Mail className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Aucun utilisateur autorisé</p>
                <p className="text-sm">Ajoutez votre premier email pour commencer</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Rôle</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead>Date d'ajout</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((userItem) => (
                    <TableRow key={userItem.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <Mail className="h-4 w-4 text-muted-foreground" />
                          {userItem.email}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={userItem.role === 'admin' ? 'default' : 'secondary'}>
                          {userItem.role === 'admin' ? (
                            <><Shield className="h-3 w-3 mr-1" /> Admin</>
                          ) : (
                            <><User className="h-3 w-3 mr-1" /> User</>
                          )}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {userItem.used_at ? (
                          <Badge variant="default" className="bg-green-600">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Actif
                          </Badge>
                        ) : userItem.is_active ? (
                          <Badge variant="secondary">
                            En attente
                          </Badge>
                        ) : (
                          <Badge variant="destructive">
                            <XCircle className="h-3 w-3 mr-1" />
                            Désactivé
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {formatDate(userItem.invited_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {!userItem.telegram_linked && userItem.used_at && userItem.user_id && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => openTelegramInvitation(userItem)}
                              title="Inviter sur Telegram"
                            >
                              <MessageCircle className="h-4 w-4 text-blue-500" />
                            </Button>
                          )}
                          {!userItem.telegram_linked && userItem.used_at && !userItem.user_id && (
                            <span 
                              className="text-xs text-orange-500 px-2"
                              title="Utilisateur non inscrit"
                            >
                              En attente d'inscription
                            </span>
                          )}
                          {userItem.telegram_linked && (
                            <Badge variant="outline" className="text-blue-600 border-blue-200 mr-2">
                              <MessageCircle className="h-3 w-3 mr-1" />
                              Telegram
                            </Badge>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleStatus(userItem.id, userItem.is_active)}
                          >
                            {userItem.is_active ? 'Désactiver' : 'Activer'}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => router.push(`/dashboard/settings/admin/users/${userItem.id}/capabilities`)}
                          >
                            <Settings className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive"
                            onClick={() => handleDelete(userItem.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Informations */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Informations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3">
                <Mail className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Pré-autorisation</p>
                  <p className="text-sm text-muted-foreground">
                    Les emails ajoutés ici pourront créer un compte sur la plateforme.
                  </p>
                </div>
              </div>
              <Separator />
              <div className="flex items-start gap-3">
                <Shield className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Rôles</p>
                  <p className="text-sm text-muted-foreground">
                    <strong>Admin :</strong> Accès complet aux paramètres<br />
                    <strong>User :</strong> Accès limité aux fonctionnalités métier
                  </p>
                </div>
              </div>
              <Separator />
              <div className="flex items-start gap-3">
                <Settings className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Permissions granulaires</p>
                  <p className="text-sm text-muted-foreground">
                    Cliquez sur l'icône <Settings className="h-3 w-3 inline" /> pour définir les droits spécifiques.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-amber-50 border-amber-200">
            <CardHeader>
              <CardTitle className="text-base text-amber-800">Bon à savoir</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-amber-700">
                Une fois l'email ajouté, l'utilisateur pourra s'inscrire depuis la page de login.
                Vous pourrez ensuite affiner ses permissions via la gestion des droits.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dialog d'invitation Telegram */}
      {selectedUserForTelegram && (
        <TelegramInvitationDialog
          isOpen={isTelegramDialogOpen}
          onClose={() => {
            setIsTelegramDialogOpen(false);
            setSelectedUserForTelegram(null);
          }}
          userId={selectedUserForTelegram.user_id || selectedUserForTelegram.id}
          userEmail={selectedUserForTelegram.email}
          userName={selectedUserForTelegram.full_name || selectedUserForTelegram.email}
        />
      )}
    </div>
  );
}
