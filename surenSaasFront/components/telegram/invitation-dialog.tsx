'use client';

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { QRCodeSVG } from "qrcode.react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Copy, Check, MessageCircle, Smartphone, Link as LinkIcon, Loader2, Send, Bot } from "lucide-react";

interface TelegramBot {
  bot_id: string;
  bot_name: string;
  description: string;
  icon: string;
  username: string;
  configured: boolean;
}

interface TelegramInvitationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  userEmail: string;
  userName: string;
}

interface InvitationData {
  telegram_link: string;
  bot_id: string;
  bot_name: string;
  bot_username: string;
  bot_icon: string;
  description: string;
  expires_at: string;
}

export function TelegramInvitationDialog({
  isOpen,
  onClose,
  userId,
  userEmail,
  userName,
}: TelegramInvitationDialogProps) {
  const [bots, setBots] = useState<TelegramBot[]>([]);
  const [selectedBot, setSelectedBot] = useState<string>("");
  const [loadingBots, setLoadingBots] = useState(false);
  const [invitation, setInvitation] = useState<InvitationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  // Charger la liste des bots quand le dialog s'ouvre
  useEffect(() => {
    if (isOpen) {
      loadBots();
    }
  }, [isOpen]);

  const loadBots = async () => {
    setLoadingBots(true);
    try {
      const response = await fetch('/api/v1/admin/telegram/bots', {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Erreur lors du chargement des bots');
      }

      const data = await response.json();
      setBots(data.bots || []);
      
      // Sélectionner le premier bot par défaut
      if (data.bots && data.bots.length > 0) {
        setSelectedBot(data.bots[0].bot_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoadingBots(false);
    }
  };

  const generateInvitation = async () => {
    console.log('🔔 generateInvitation appelé avec userId:', userId);
    
    if (!selectedBot) {
      setError("Veuillez sélectionner un bot");
      return;
    }

    if (!userId) {
      console.error('❌ userId est undefined ou null !');
      setError("ID utilisateur manquant. Veuillez réessayer.");
      return;
    }

    setLoading(true);
    setError("");
    
    try {
      console.log('📡 Appel API avec userId:', userId);
      const response = await fetch(`/api/v1/admin/users/${userId}/telegram-invitation`, {
        method: "POST",
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: "include",
        body: JSON.stringify({
          bot_id: selectedBot,
          expires_in_hours: 168 // 7 jours
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Erreur lors de la génération de l'invitation");
      }

      const data = await response.json();
      console.log('✅ Invitation reçue:', data);
      console.log('🔗 Lien Telegram:', data.telegram_link);
      setInvitation(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const shareViaEmail = () => {
    if (!invitation) return;
    
    const subject = encodeURIComponent(`Invitation à rejoindre Suren ${invitation.bot_name} sur Telegram`);
    const body = encodeURIComponent(
      `Bonjour ${userName},\n\n` +
      `Vous êtes invité à rejoindre Suren ${invitation.bot_name} Bot sur Telegram.\n\n` +
      `${invitation.description}\n\n` +
      `Cliquez sur ce lien pour commencer : ${invitation.telegram_link}\n\n` +
      `Ou scannez le QR code ci-joint.\n\n` +
      `Cordialement,\nL'équipe Suren`
    );
    
    window.open(`mailto:${userEmail}?subject=${subject}&body=${body}`, "_blank");
  };

  // Réinitialiser quand le dialog se ferme
  const handleClose = () => {
    setInvitation(null);
    setError("");
    setCopied(false);
    setSelectedBot("");
    setBots([]);
    onClose();
  };

  const selectedBotData = bots.find(b => b.bot_id === selectedBot);

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5 text-blue-500" />
            Inviter sur Telegram
          </DialogTitle>
          <DialogDescription>
            Envoyez une invitation à {userName} pour rejoindre un bot Telegram
          </DialogDescription>
        </DialogHeader>

        {!invitation ? (
          <div className="space-y-4 py-4">
            {loadingBots ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : bots.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Bot className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Aucun bot Telegram configuré</p>
                <p className="text-sm">Contactez votre administrateur système</p>
              </div>
            ) : (
              <>
                {/* Sélection du bot */}
                <div className="space-y-2">
                  <Label htmlFor="bot-select">Sélectionner un bot</Label>
                  <Select value={selectedBot} onValueChange={setSelectedBot}>
                    <SelectTrigger id="bot-select">
                      <SelectValue placeholder="Choisir un bot..." />
                    </SelectTrigger>
                    <SelectContent>
                      {bots.map((bot) => (
                        <SelectItem key={bot.bot_id} value={bot.bot_id}>
                          <div className="flex items-center gap-2">
                            <span>{bot.icon}</span>
                            <span>{bot.bot_name}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  {selectedBotData && (
                    <p className="text-sm text-muted-foreground">
                      {selectedBotData.description}
                    </p>
                  )}
                </div>

                <Card className="bg-blue-50 border-blue-200">
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-3">
                      <Smartphone className="h-5 w-5 text-blue-600 mt-0.5" />
                      <div>
                        <p className="font-medium text-sm text-blue-900">Comment ça marche ?</p>
                        <p className="text-sm text-blue-700 mt-1">
                          L'utilisateur recevra un lien pour ouvrir Telegram et lier son compte. 
                          Il pourra ensuite utiliser les fonctionnalités du bot sélectionné.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {error && (
                  <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">
                    {error}
                  </div>
                )}

                <Button 
                  onClick={generateInvitation}
                  disabled={loading || !selectedBot}
                  className="w-full bg-gradient-to-r from-blue-600 to-violet-600"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Génération...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Générer l'invitation
                    </>
                  )}
                </Button>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-4 py-4">
            {/* QR Code */}
            <div className="flex flex-col items-center space-y-3">
              <div className="p-4 bg-white rounded-lg border-2 border-gray-100">
                <QRCodeSVG
                  value={invitation.telegram_link}
                  size={180}
                  level="M"
                  includeMargin={false}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                Scannez pour ouvrir Telegram
              </p>
            </div>

            {/* Lien direct */}
            <div className="space-y-2">
              <Label>Lien d'invitation</Label>
              <div className="flex gap-2">
                <Input
                  value={invitation.telegram_link}
                  readOnly
                  className="font-mono text-xs"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => copyToClipboard(invitation.telegram_link)}
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Bot info */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="text-xl">{invitation.bot_icon}</span>
              <span>Bot {invitation.bot_name} : @{invitation.bot_username}</span>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => copyToClipboard(invitation.telegram_link)}
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Copié !
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Copier le lien
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                onClick={shareViaEmail}
              >
                <LinkIcon className="h-4 w-4 mr-2" />
                Envoyer par email
              </Button>
            </div>

            {invitation.expires_at && (
              <p className="text-xs text-muted-foreground text-center">
                Ce lien expire le {new Date(invitation.expires_at).toLocaleDateString('fr-FR')}
              </p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
