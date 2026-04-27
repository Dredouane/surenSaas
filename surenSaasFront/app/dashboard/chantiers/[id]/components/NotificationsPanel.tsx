'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Bell,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  User,
  FileText,
  Target,
  Users,
  MessageSquare,
  ExternalLink,
  Filter,
  Download,
  Send,
  RefreshCw,
} from 'lucide-react';
import { Notification, NotificationType } from '@/types/chantier';

interface NotificationsPanelProps {
  chantierId: string;
  orgId: string;
  onRefresh?: () => void;
  botUsername?: string;
}

export default function NotificationsPanel({ chantierId, orgId, onRefresh, botUsername = "@SurenSaasBot" }: NotificationsPanelProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newNotification, setNewNotification] = useState({
    type: 'info' as NotificationType,
    titre: '',
    message: '',
    lienValidation: '',
  });

  useEffect(() => {
    fetchNotifications();
  }, [chantierId]);

  const fetchNotifications = async () => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/notifications?org_id=${orgId}`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.map((n: any) => ({
          id: n.id,
          userId: n.user_id || '',
          type: n.type || 'info',
          entityType: n.entity_type || 'chantier',
          entityId: n.chantier_id || '',
          titre: n.titre,
          message: n.message,
          url: n.url || '',
          statut: n.statut || 'envoyee',
          telegramMessageId: n.telegram_message_id || '',
          createdAt: n.created_at,
        })));
      }
    } catch (err) {
      console.error('Erreur chargement notifications:', err);
    }
  };

  // Filtrer les notifications
  const filteredNotifications = notifications.filter(notification => {
    const matchesSearch = notification.titre.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         notification.message.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = selectedType === 'all' || notification.type === selectedType;
    const matchesStatus = selectedStatus === 'all' || notification.statut === selectedStatus;
    return matchesSearch && matchesType && matchesStatus;
  });

  // Obtenir la couleur du badge selon le type
  const getTypeBadge = (type: NotificationType) => {
    switch (type) {
      case 'info':
        return <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Information</Badge>;
      case 'alerte':
        return <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">Alerte</Badge>;
      case 'urgence':
        return <Badge className="bg-red-100 text-red-800 hover:bg-red-100">Urgence</Badge>;
      case 'validation':
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Validation</Badge>;
      case 'tache':
        return <Badge className="bg-purple-100 text-purple-800 hover:bg-purple-100">Tâche</Badge>;
      case 'reception':
        return <Badge className="bg-indigo-100 text-indigo-800 hover:bg-indigo-100">Réception</Badge>;
      case 'pointage':
        return <Badge className="bg-cyan-100 text-cyan-800 hover:bg-cyan-100">Pointage</Badge>;
      default:
        return <Badge variant="outline">{type}</Badge>;
    }
  };

  // Obtenir la couleur du badge selon le statut
  const getStatutBadge = (statut: string) => {
    switch (statut) {
      case 'envoyee':
        return <Badge className="bg-gray-100 text-gray-800 hover:bg-gray-100">Envoyée</Badge>;
      case 'lue':
        return <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Lue</Badge>;
      case 'validee':
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Validée</Badge>;
      case 'refusee':
        return <Badge className="bg-red-100 text-red-800 hover:bg-red-100">Refusée</Badge>;
      case 'en_attente':
        return <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">En attente</Badge>;
      default:
        return <Badge variant="outline">{statut}</Badge>;
    }
  };

  // Obtenir l'icône selon le type
  const getTypeIcon = (type: NotificationType) => {
    switch (type) {
      case 'info':
        return <Bell className="h-4 w-4" />;
      case 'alerte':
        return <AlertCircle className="h-4 w-4" />;
      case 'urgence':
        return <AlertCircle className="h-4 w-4" />;
      case 'validation':
        return <CheckCircle className="h-4 w-4" />;
      case 'tache':
        return <Target className="h-4 w-4" />;
      case 'reception':
        return <FileText className="h-4 w-4" />;
      case 'pointage':
        return <Users className="h-4 w-4" />;
      default:
        return <Bell className="h-4 w-4" />;
    }
  };

  // Formater une date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', { 
      day: 'numeric', 
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Handler pour envoyer une notification
  const handleSendNotification = async () => {
    if (!newNotification.titre || !newNotification.message) return;
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/notifications?org_id=${orgId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: newNotification.type,
          titre: newNotification.titre,
          message: newNotification.message,
          url: newNotification.lienValidation || undefined,
          statut: 'envoyee',
        }),
      });
      if (!res.ok) throw new Error('Erreur envoi notification');
      setShowCreateDialog(false);
      setNewNotification({ type: 'info', titre: '', message: '', lienValidation: '' });
      fetchNotifications();
      onRefresh?.();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  // Handler pour marquer comme lu
  const handleMarkAsRead = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/chantiers/${chantierId}/notifications/${id}?org_id=${orgId}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ statut: 'lue' }),
      });
      if (!res.ok) throw new Error('Erreur mise à jour notification');
      fetchNotifications();
      onRefresh?.();
    } catch (err) {
      alert('Erreur : ' + (err instanceof Error ? err.message : 'Erreur inconnue'));
    }
  };

  // Handler pour rafraîchir les notifications
  const handleRefreshNotifications = () => {
    fetchNotifications();
    onRefresh?.();
  };

  // Handler pour exporter
  const handleExport = () => {
    alert('Export des notifications au format CSV');
  };

  // Statistiques
  const stats = {
    total: notifications.length,
    nonLues: notifications.filter(n => n.statut === 'envoyee' || n.statut === 'en_attente').length,
    validees: notifications.filter(n => n.statut === 'validee').length,
    urgentes: notifications.filter(n => n.type === 'urgence').length,
  };

  return (
    <div className="space-y-6">
      {/* En-tête avec actions */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Système de notifications</h2>
          <p className="text-muted-foreground">
            Notifications push bi-directionnelles via Telegram avec validation
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant="outline" onClick={handleRefreshNotifications} className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Rafraîchir
          </Button>
          <Button variant="outline" onClick={handleExport} className="gap-2">
            <Download className="h-4 w-4" />
            Exporter
          </Button>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Send className="h-4 w-4" />
                Nouvelle notification
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Envoyer une notification</DialogTitle>
                <DialogDescription>
                  Envoyez une notification push via Telegram au conducteur ou au gérant
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="type">Type</Label>
                  <Select
                    value={newNotification.type}
                    onValueChange={(value) => setNewNotification({...newNotification, type: value as NotificationType})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="info">Information</SelectItem>
                      <SelectItem value="alerte">Alerte</SelectItem>
                      <SelectItem value="urgence">Urgence</SelectItem>
                      <SelectItem value="validation">Validation</SelectItem>
                      <SelectItem value="tache">Tâche</SelectItem>
                      <SelectItem value="reception">Réception</SelectItem>
                      <SelectItem value="pointage">Pointage</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="titre">Titre</Label>
                  <Input
                    id="titre"
                    placeholder="Titre de la notification"
                    value={newNotification.titre}
                    onChange={(e) => setNewNotification({...newNotification, titre: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="message">Message</Label>
                  <Input
                    id="message"
                    placeholder="Message détaillé"
                    value={newNotification.message}
                    onChange={(e) => setNewNotification({...newNotification, message: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lien">Lien de validation (optionnel)</Label>
                  <Input
                    id="lien"
                    placeholder="https://..."
                    value={newNotification.lienValidation}
                    onChange={(e) => setNewNotification({...newNotification, lienValidation: e.target.value})}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                  Annuler
                </Button>
                <Button onClick={handleSendNotification} disabled={!newNotification.titre || !newNotification.message}>
                  Envoyer via Telegram
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Statistiques */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total notifications</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Bell className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Non lues</p>
                <p className="text-2xl font-bold text-amber-600">{stats.nonLues}</p>
              </div>
              <AlertCircle className="h-8 w-8 text-amber-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Validées</p>
                <p className="text-2xl font-bold text-green-600">{stats.validees}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Urgentes</p>
                <p className="text-2xl font-bold text-red-600">{stats.urgentes}</p>
              </div>
              <AlertCircle className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filtres */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search">Recherche</Label>
              <Input
                id="search"
                placeholder="Titre, message, destinataire..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type-filter">Type</Label>
              <Select value={selectedType} onValueChange={setSelectedType}>
                <SelectTrigger>
                  <SelectValue placeholder="Tous les types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les types</SelectItem>
                  <SelectItem value="info">Information</SelectItem>
                  <SelectItem value="alerte">Alerte</SelectItem>
                  <SelectItem value="urgence">Urgence</SelectItem>
                  <SelectItem value="validation">Validation</SelectItem>
                  <SelectItem value="tache">Tâche</SelectItem>
                  <SelectItem value="reception">Réception</SelectItem>
                  <SelectItem value="pointage">Pointage</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="status-filter">Statut</Label>
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Tous les statuts" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="envoyee">Envoyée</SelectItem>
                  <SelectItem value="lue">Lue</SelectItem>
                  <SelectItem value="validee">Validée</SelectItem>
                  <SelectItem value="refusee">Refusée</SelectItem>
                  <SelectItem value="en_attente">En attente</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tableau des notifications */}
      <Card>
        <CardHeader>
          <CardTitle>Historique des notifications</CardTitle>
          <p className="text-sm text-muted-foreground">
            {filteredNotifications.length} notification(s) trouvée(s)
          </p>
        </CardHeader>
        <CardContent>
          {filteredNotifications.length === 0 ? (
            <div className="text-center py-12">
              <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium">Aucune notification trouvée</h3>
              <p className="text-muted-foreground mt-2">
                Les notifications apparaîtront ici lorsqu'elles seront envoyées via Telegram.
              </p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Titre</TableHead>
                    <TableHead>Destinataire</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredNotifications.map((notification) => (
                    <TableRow key={notification.id} className={notification.statut === 'envoyee' ? 'bg-blue-50' : ''}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getTypeIcon(notification.type)}
                          {getTypeBadge(notification.type)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium">{notification.titre}</p>
                          <p className="text-sm text-muted-foreground truncate max-w-xs">
                            {notification.message}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-muted-foreground" />
                          <div>
                            <p className="font-medium">
                              {notification.userId.includes('mohsan') ? 'Conducteur' : 'Gérant'}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4 text-muted-foreground" />
                          {formatDate(String(notification.createdAt))}
                        </div>
                      </TableCell>
                      <TableCell>
                        {getStatutBadge(notification.statut)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {notification.url && (
                            <Button variant="ghost" size="sm" className="gap-1 h-8">
                              <ExternalLink className="h-3 w-3" />
                              Lien
                            </Button>
                          )}
                          {notification.statut === 'envoyee' && (
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-8 w-8 p-0"
                              onClick={() => handleMarkAsRead(notification.id)}
                            >
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                          )}
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <MessageSquare className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Workflow Telegram */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Workflow Telegram - Notifications bi-directionnelles
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Architecture des notifications push avec validation
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Diagramme de workflow */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="border rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="font-bold text-blue-600">1</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Événement déclencheur</h4>
                    <p className="text-sm text-muted-foreground">Réception, tâche, pointage</p>
                  </div>
                </div>
                <p className="text-sm">
                  Un événement nécessite une action (validation, information, alerte).
                </p>
              </div>
              <div className="border rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                    <span className="font-bold text-green-600">2</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Notification Telegram</h4>
                    <p className="text-sm text-muted-foreground">Push avec boutons inline</p>
                  </div>
                </div>
                <p className="text-sm">
                  Notification envoyée avec lien vers la page de validation détaillée.
                </p>
              </div>
              <div className="border rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-10 w-10 rounded-full bg-purple-100 flex items-center justify-center">
                    <span className="font-bold text-purple-600">3</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Validation & Feedback</h4>
                    <p className="text-sm text-muted-foreground">Boutons Oui/Non/Modifier</p>
                  </div>
                </div>
                <p className="text-sm">
                  Le destinataire valide via Telegram. Notification de confirmation envoyée en retour.
                </p>
              </div>
            </div>

            <Separator />

            {/* Exemples de notifications */}
            <div>
              <h4 className="font-medium mb-4">Exemples de notifications</h4>
              <div className="space-y-3">
                <div className="border rounded-lg p-3 bg-blue-50">
                  <div className="flex items-center gap-2 mb-1">
                    <Target className="h-4 w-4 text-blue-600" />
                    <span className="font-medium">Nouvelle tâche assignée</span>
                  </div>
                  <p className="text-sm">
                    <strong>Conducteur</strong>: Vous avez une nouvelle tâche "Vérification fondations". 
                    <a href="#" className="text-blue-600 ml-1">Voir les détails →</a>
                  </p>
                  <div className="flex gap-2 mt-2">
                    <Button size="sm" className="h-6 text-xs">Accepter</Button>
                    <Button size="sm" variant="outline" className="h-6 text-xs">Refuser</Button>
                    <Button size="sm" variant="outline" className="h-6 text-xs">Demander modifications</Button>
                  </div>
                </div>
                <div className="border rounded-lg p-3 bg-green-50">
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="h-4 w-4 text-green-600" />
                    <span className="font-medium">Pointage validé</span>
                  </div>
                  <p className="text-sm">
                    <strong>Gérant</strong>: Le conducteur a validé les pointages du 21/04. 
                    5 hommes et 3 machines présents. <a href="#" className="text-green-600 ml-1">Voir le rapport →</a>
                  </p>
                </div>
                <div className="border rounded-lg p-3 bg-amber-50">
                  <div className="flex items-center gap-2 mb-1">
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                    <span className="font-medium">Réception client en retard</span>
                  </div>
                  <p className="text-sm">
                    <strong>Gérant</strong>: La réception client prévue à 14h est en retard de 30 minutes. 
                    <a href="#" className="text-amber-600 ml-1">Contacter le client →</a>
                  </p>
                </div>
              </div>
            </div>

            <Separator />

            {/* Configuration */}
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">Configuration Telegram</h4>
                <p className="text-sm text-muted-foreground">
                  Bot: {botUsername} • Dernière synchronisation: Aujourd'hui 08:30
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  Tester connexion
                </Button>
                <Button variant="outline" size="sm">
                  Voir logs
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Note prototype */}
      <div className="text-sm text-muted-foreground border-t pt-4">
        <p>
          <strong>Note prototype:</strong> Cette interface unifie toutes les notifications des 3 nouvelles fonctionnalités (réceptions, tâches, pointages).
          Le système de notifications push via Telegram avec validation bi-directionnelle est démontré ici avec des données statiques.
          L'intégration réelle avec le bot Telegram ConstructionBotService sera implémentée dans la prochaine itération.
        </p>
      </div>
    </div>
  );
}