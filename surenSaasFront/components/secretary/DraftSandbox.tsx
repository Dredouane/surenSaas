'use client';

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { 
  X, 
  Edit3, 
  Send, 
  Copy, 
  Check,
  Scissors,
  Crown,
  Signature,
  Wrench,
  Loader2
} from "lucide-react";

interface DraftSandboxProps {
  threadId: string;
  orgSlug: string;
  onClose: () => void;
}

interface Draft {
  content: string;
  plainText: string;
  suggestions: string[];
}

export function DraftSandbox({ threadId, orgSlug, onClose }: DraftSandboxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [instruction, setInstruction] = useState("");
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Générer le draft initial
  const generateDraft = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/v1/${orgSlug}/email-threads/${threadId}/draft`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ context_level: 'full', tone: 'professional' }),
        }
      );

      if (response.ok) {
        const data = await response.json();
        // Mapper snake_case → camelCase
        setDraft({
          content: data.content,
          plainText: data.plain_text,
          suggestions: data.suggestions
        });
      } else {
        // Fallback si API indisponible
        setDraft({
          content: "<p>Bonjour,</p><p>Merci pour votre message. Je reviens vers vous rapidement.</p><p>Cordialement,</p>",
          plainText: "Bonjour,\n\nMerci pour votre message. Je reviens vers vous rapidement.\n\nCordialement,",
          suggestions: ["shorten", "formal", "add_signature"]
        });
      }
    } catch (err) {
      console.error('Erreur génération draft:', err);
      // Fallback
      setDraft({
        content: "<p>Bonjour,</p><p>Merci pour votre message. Je reviens vers vous rapidement.</p><p>Cordialement,</p>",
        plainText: "Bonjour,\n\nMerci pour votre message. Je reviens vers vous rapidement.\n\nCordialement,",
        suggestions: ["shorten", "formal", "add_signature"]
      });
    } finally {
      setLoading(false);
    }
  };

  // Itérer sur le draft
  const iterateDraft = async () => {
    if (!draft || !instruction.trim()) return;
    
    setLoading(true);
    try {
      const response = await fetch(
        `/api/v1/${orgSlug}/email-threads/${threadId}/draft/temp-iterate`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            current_content: draft.content,
            instruction: instruction,
            action: 'iterate'
          }),
        }
      );

      if (response.ok) {
        const data = await response.json();
        // Mapper snake_case → camelCase
        setDraft({
          content: data.content,
          plainText: data.plain_text,
          suggestions: data.suggestions
        });
        setInstruction("");
      }
    } catch (err) {
      console.error('Erreur itération:', err);
    } finally {
      setLoading(false);
    }
  };

  // Appliquer un Smart Chip
  const applySmartChip = async (chipId: string) => {
    if (!draft) return;
    
    // Simuler les transformations côté client pour l'instant
    setLoading(true);
    
    setTimeout(() => {
      let newText = draft.plainText;
      
      switch (chipId) {
        case 'shorten':
          newText = newText.split('\n').slice(0, 3).join('\n') + '\n\nCordialement,';
          break;
        case 'formal':
          newText = newText.replace(/Bonjour,/, 'Bonjour Madame, Monsieur,');
          break;
        case 'add_signature':
          newText += '\n\n--\nVotre entreprise\nTél: 01 23 45 67 89';
          break;
        case 'technical':
          newText = newText.replace(/travaux/, 'travaux de rénovation technique');
          break;
      }
      
      setDraft({
        ...draft,
        plainText: newText
      });
      setLoading(false);
    }, 500);
  };

  // Copier dans le clipboard
  const copyToClipboard = () => {
    if (!draft) return;
    navigator.clipboard.writeText(draft.plainText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Ouvrir le sandbox
  const openSandbox = () => {
    setIsOpen(true);
    generateDraft();
  };

  // Fermer le sandbox
  const handleClose = () => {
    setIsOpen(false);
    setDraft(null);
    onClose();
  };

  if (!isOpen) {
    return (
      <Button
        onClick={openSandbox}
        variant="outline"
        size="sm"
        className="gap-2"
      >
        <Edit3 className="h-4 w-4" />
        Préparer une réponse
      </Button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Edit3 className="h-5 w-5 text-blue-600" />
            <h3 className="font-semibold">Rédiger une réponse</h3>
          </div>
          <Button variant="ghost" size="icon" onClick={handleClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loading && !draft ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <span className="ml-2 text-muted-foreground">Génération du draft...</span>
            </div>
          ) : draft ? (
            <>
              {/* Editor */}
              <div>
                <Textarea
                  ref={textareaRef}
                  value={draft.plainText}
                  onChange={(e) => setDraft({ ...draft, plainText: e.target.value })}
                  className="min-h-[200px] font-mono text-sm"
                  placeholder="Votre réponse..."
                />
              </div>

              {/* Smart Chips */}
              <div className="flex flex-wrap gap-2">
                <Badge 
                  variant="secondary" 
                  className="cursor-pointer hover:bg-blue-100"
                  onClick={() => applySmartChip('shorten')}
                >
                  <Scissors className="h-3 w-3 mr-1" />
                  Plus court
                </Badge>
                <Badge 
                  variant="secondary" 
                  className="cursor-pointer hover:bg-blue-100"
                  onClick={() => applySmartChip('formal')}
                >
                  <Crown className="h-3 w-3 mr-1" />
                  Plus poli
                </Badge>
                <Badge 
                  variant="secondary" 
                  className="cursor-pointer hover:bg-blue-100"
                  onClick={() => applySmartChip('add_signature')}
                >
                  <Signature className="h-3 w-3 mr-1" />
                  Ajouter signature
                </Badge>
                <Badge 
                  variant="secondary" 
                  className="cursor-pointer hover:bg-blue-100"
                  onClick={() => applySmartChip('technical')}
                >
                  <Wrench className="h-3 w-3 mr-1" />
                  Plus technique
                </Badge>
              </div>

              {/* Petit Prompt */}
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Instructions complémentaires... (ex: 'Ajouter une date butoir')"
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && iterateDraft()}
                  className="flex-1 px-3 py-2 border rounded-md text-sm"
                />
                <Button 
                  size="sm" 
                  onClick={iterateDraft}
                  disabled={loading || !instruction.trim()}
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t bg-gray-50">
          <Button variant="ghost" size="sm" onClick={handleClose}>
            Annuler
          </Button>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={copyToClipboard}
              disabled={!draft}
              className="gap-2"
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? "Copié !" : "Copier"}
            </Button>
            <Button
              size="sm"
              onClick={() => {
                copyToClipboard();
                handleClose();
              }}
              disabled={!draft}
              className="gap-2"
            >
              <Check className="h-4 w-4" />
              Valider & copier
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
