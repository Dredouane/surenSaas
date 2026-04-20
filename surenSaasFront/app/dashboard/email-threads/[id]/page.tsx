"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/app/contexts/AuthContext";
import { useIsMobile } from "@/hooks/use-media-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import {
  Send,
  Bot,
  User,
  Mail,
  Paperclip,
  ArrowLeft,
  Clock,
  Flag,
  CheckCircle2,
  AlertCircle,
  MessageSquare,
  History,
} from "lucide-react";
import Link from "next/link";
import { DraftSandbox } from "@/components/secretary/DraftSandbox";

interface Email {
  id: string;
  role: "client" | "toi";
  sender: {
    email: string;
    name?: string;
  };
  subject: string;
  content: {
    text?: string;
    html?: string;
  };
  sent_at: string;
  has_attachments: boolean;
  attachments?: Array<{
    filename: string;
    mime_type: string;
  }>;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

const statusLabels: Record<string, { label: string; color: string }> = {
  new: { label: "Nouveau", color: "bg-blue-100 text-blue-800" },
  in_progress: { label: "En cours", color: "bg-yellow-100 text-yellow-800" },
  waiting: { label: "En attente", color: "bg-orange-100 text-orange-800" },
  resolved: { label: "Résolu", color: "bg-green-100 text-green-800" },
};

const urgencyLabels: Record<string, { label: string; color: string }> = {
  low: { label: "Basse", color: "bg-gray-100 text-gray-600" },
  medium: { label: "Moyenne", color: "bg-yellow-100 text-yellow-700" },
  high: { label: "Haute", color: "bg-red-100 text-red-700" },
};

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffTime = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  } else if (diffDays === 1) {
    return "Hier";
  } else if (diffDays < 7) {
    const days = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"];
    return days[date.getDay()];
  } else {
    return date.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
  }
}

function formatFullDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function EmailThreadDetailPage() {
  const params = useParams();
  const { user } = useAuth();
  const threadId = params.id as string;
  const isMobile = useIsMobile();

  const [thread, setThread] = useState<{
    id: string;
    subject: string;
    subject_cleaned?: string;
    participants: {
      emails: string[];
      names: string[];
    };
    ai_summary?: string;
    ai_urgency?: "low" | "medium" | "high";
    ai_status?: "new" | "in_progress" | "waiting" | "resolved";
    metrics: {
      email_count: number;
      attachment_count: number;
      first_email_at: string | null;
      last_email_at: string | null;
    };
    flags: {
      is_archived: boolean;
      is_starred: boolean;
    };
    emails?: Email[];
    created_at: string;
    updated_at: string;
    is_historical_partial?: boolean;
    historical_notes?: string;
  } | null>(null);

  const [emails, setEmails] = useState<Email[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"conversation" | "assistant">("conversation");
  const [showDraftSandbox, setShowDraftSandbox] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user?.org_slug && threadId) {
      fetchThreadDetails();
    }
  }, [user?.org_slug, threadId]);

  useEffect(() => {
    if (user?.org_slug && threadId) {
      fetchChatMessages();
    }
  }, [user?.org_slug, threadId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const fetchThreadDetails = async () => {
    if (!user?.org_slug || !threadId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/${user.org_slug}/email-threads/${threadId}`
      );
      if (!response.ok) {
        throw new Error("Erreur lors du chargement de la conversation");
      }

      const data = await response.json();
      setThread(data);
      setEmails(data.emails || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Une erreur est survenue");
    } finally {
      setLoading(false);
    }
  };

  const fetchChatMessages = async () => {
    if (!user?.org_slug || !threadId) return;

    try {
      const response = await fetch(
        `/api/v1/${user.org_slug}/email-threads/${threadId}/chat`
      );
      if (!response.ok) {
        throw new Error("Erreur lors du chargement du chat");
      }

      const data = await response.json();
      setChatMessages(data.messages || []);
    } catch (err) {
      console.error("Failed to fetch chat messages:", err);
    }
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !user?.org_slug || !threadId || sending) return;

    const userMessage = chatInput.trim();
    setChatInput("");
    setSending(true);

    // Optimistically add user message
    const tempUserMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, tempUserMessage]);

    try {
      const response = await fetch(
        `/api/v1/${user.org_slug}/email-threads/${threadId}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userMessage }),
        }
      );

      if (!response.ok) {
        throw new Error("Erreur lors de l'envoi du message");
      }

      const data = await response.json();
      
      // Remove temp message and add real messages
      setChatMessages((prev) =>
        prev.filter((m) => m.id !== tempUserMessage.id)
      );
      setChatMessages((prev) => [...prev, data.user_message, data.assistant_message]);
    } catch (err) {
      console.error("Failed to send message:", err);
      // Remove temp message on error
      setChatMessages((prev) =>
        prev.filter((m) => m.id !== tempUserMessage.id)
      );
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (loading) {
    return (
      <div className="h-screen flex flex-col md:flex-row overflow-hidden">
        {/* Mobile: full width, Desktop: 55% */}
        <div className="w-full md:w-[55%] flex flex-col border-r bg-gray-50">
          <div className="bg-white border-b p-4">
            <Skeleton className="h-8 w-24 mb-4" />
            <div className="space-y-4">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          </div>
        </div>
        {/* Desktop: right side */}
        <div className="hidden md:block md:w-[45%] bg-white">
          <div className="p-4 space-y-4">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !thread) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Erreur</h2>
          <p className="text-gray-500 mb-4">{error || "Conversation non trouvée"}</p>
          <Link href="/dashboard/email-threads">
            <Button>Retour aux emails</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Composant Conversation Panel
  const ConversationPanel = () => (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b p-4">
        <Link href="/dashboard/email-threads">
          <Button variant="ghost" size="sm" className="mb-2">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retour
          </Button>
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              {thread.subject || "(Pas de sujet)"}
            </h1>
            <p className="text-base text-gray-600 mt-1">
              De: {thread.participants?.names?.[0] || thread.participants?.emails?.[0] || "-"}
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Badge
              className={statusLabels[thread.ai_status || "new"]?.color || "bg-gray-100"}
              variant="secondary"
            >
              {statusLabels[thread.ai_status || "new"]?.label || thread.ai_status}
            </Badge>
            {thread.ai_urgency && thread.ai_urgency !== "low" && (
              <Badge
                className={urgencyLabels[thread.ai_urgency]?.color || "bg-gray-100"}
                variant="secondary"
              >
                {urgencyLabels[thread.ai_urgency]?.label}
              </Badge>
            )}
            {thread.is_historical_partial && (
              <Badge
                className="bg-gray-100 text-gray-600 border border-gray-300"
                variant="secondary"
                title={thread.historical_notes || "Historique partiel"}
              >
                <History className="h-3 w-3 mr-1" />
                Partiel
              </Badge>
            )}
            {thread.flags?.is_starred && (
              <Flag className="h-5 w-5 text-red-500" />
            )}
          </div>
        </div>

        {thread.ai_summary && (
          <div className="mt-3 p-3 bg-blue-50 rounded-lg">
            <p className="text-base text-blue-900">
              <span className="font-semibold">Résumé IA:</span> {thread.ai_summary}
            </p>
          </div>
        )}
      </div>

      {/* Email List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {emails.map((email) => (
          <Card key={email.id}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="text-base bg-gradient-to-br from-blue-500 to-purple-600 text-white">
                      {(email.sender?.name || email.sender?.email || "?").charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="text-base font-medium">
                      {email.sender?.name || email.sender?.email || "-"}
                    </p>
                    <p className="text-sm text-gray-500">{email.sender?.email || "-"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Clock className="h-3 w-3" />
                  {email.sent_at ? formatFullDate(email.sent_at) : "-"}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {email.content?.html ? (
                <div
                  className="prose prose-base max-w-none text-gray-800"
                  dangerouslySetInnerHTML={{ __html: email.content.html }}
                />
              ) : (
                <pre className="whitespace-pre-wrap text-base text-gray-800 font-sans">
                  {email.content?.text || "(Pas de contenu)"}
                </pre>
              )}

              {email.has_attachments && (
                <div className="mt-4 flex items-center gap-2 text-base text-gray-600">
                  <Paperclip className="h-4 w-4" />
                  <span>Pièces jointes</span>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );

  // Composant Assistant Panel
  const AssistantPanel = () => (
    <div className="flex flex-col h-full bg-white">
      {/* Chat Header */}
      <div className="border-b p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900 text-lg">Assistant IA</h2>
            <p className="text-sm text-gray-500">Secrétaire virtuelle</p>
          </div>
        </div>
        
        {/* Draft Sandbox Trigger */}
        {user?.org_slug && (
          <DraftSandbox
            threadId={threadId}
            orgSlug={user.org_slug}
            onClose={() => setShowDraftSandbox(false)}
          />
        )}
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatMessages.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Bot className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p className="text-base">Commencez à discuter avec l&apos;assistant IA</p>
            <p className="text-base">Posez des questions sur cet email ou demandez de l&apos;aide</p>
          </div>
        )}

        {chatMessages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.role === "user" ? "flex-row-reverse" : ""
            }`}
          >
            <Avatar className="h-8 w-8 flex-shrink-0">
              <AvatarFallback
                className={
                  message.role === "assistant"
                    ? "bg-gradient-to-br from-indigo-500 to-purple-600 text-white"
                    : "bg-gray-200 text-gray-700"
                }
              >
                {message.role === "assistant" ? (
                  <Bot className="h-4 w-4" />
                ) : (
                  <User className="h-4 w-4" />
                )}
              </AvatarFallback>
            </Avatar>

            <div
              className={`max-w-[85%] md:max-w-[80%] rounded-lg p-3 ${
                message.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              <p className="text-base whitespace-pre-wrap leading-relaxed">{message.content}</p>
              <p
                className={`text-sm mt-1 ${
                  message.role === "user" ? "text-blue-200" : "text-gray-500"
                }`}
              >
                {formatDate(message.created_at)}
              </p>
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex gap-3">
            <Avatar className="h-8 w-8 flex-shrink-0">
              <AvatarFallback className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
                <Bot className="h-4 w-4" />
              </AvatarFallback>
            </Avatar>
            <div className="bg-gray-100 rounded-lg p-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.1s]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Chat Input */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Textarea
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Écrivez votre message..."
            className="flex-1 min-h-[60px] max-h-[120px] resize-none text-base"
            disabled={sending}
          />
          <Button
            onClick={handleSendMessage}
            disabled={!chatInput.trim() || sending}
            className="self-end"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-sm text-gray-500 mt-2">
          Appuyez sur Entrée pour envoyer, Maj+Entrée pour une nouvelle ligne
        </p>
      </div>
    </div>
  );

  // Layout responsive
  return (
    <div className="h-screen flex flex-col md:flex-row overflow-hidden bg-white">
      {/* Mobile: Tabs */}
      {isMobile && (
        <div className="flex border-b bg-white">
          <button
            onClick={() => setActiveTab("conversation")}
            className={`flex-1 flex items-center justify-center gap-2 py-3 text-base font-medium ${
              activeTab === "conversation"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-600"
            }`}
          >
            <MessageSquare className="h-5 w-5" />
            Conversation
          </button>
          <button
            onClick={() => setActiveTab("assistant")}
            className={`flex-1 flex items-center justify-center gap-2 py-3 text-base font-medium ${
              activeTab === "assistant"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-600"
            }`}
          >
            <Bot className="h-5 w-5" />
            Assistant IA
          </button>
        </div>
      )}

      {/* Content */}
      {isMobile ? (
        // Mobile: Show active tab
        <div className="flex-1 overflow-hidden">
          {activeTab === "conversation" ? <ConversationPanel /> : <AssistantPanel />}
        </div>
      ) : (
        // Desktop: Split screen
        <>
          <div className="w-[55%] flex flex-col border-r overflow-hidden">
            <ConversationPanel />
          </div>
          <div className="w-[45%] flex flex-col overflow-hidden">
            <AssistantPanel />
          </div>
        </>
      )}
    </div>
  );
}
