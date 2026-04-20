"use client";

/**
 * Page Import Dossier AO
 * 
 * Permet d'uploader un dossier ZIP contenant les documents d'un AO
 * pour créer automatiquement une candidature avec analyse des métadonnées.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { FolderUploader } from "@/components/ao/FolderUploader";
import { ArrowLeft, FileText, Sparkles, Brain, Zap } from "lucide-react";

export default function ImportFolderPage() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link href="/dashboard/ao">
          <Button variant="outline" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Importer un dossier AO</h1>
          <p className="text-muted-foreground">
            Créez automatiquement une candidature à partir d&apos;un dossier de documents
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Colonne principale - Upload */}
        <div className="lg:col-span-2">
          <FolderUploader
            onSuccess={(candidatureId) => {
              // Optionnel: rediriger automatiquement après succès
              // router.push(`/dashboard/ao/${candidatureId}`);
            }}
          />
        </div>

        {/* Colonne latérale - Instructions */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-yellow-500" />
                Analyse automatique
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-gray-600 space-y-2">
              <p>
                Notre IA analyse automatiquement vos documents pour extraire :
              </p>
              <ul className="space-y-1 text-sm">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                  Nom du projet
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                  Client / Maître d&apos;ouvrage
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                  Référence de l&apos;AO
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                  Dates limites
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                  Montant total (BPU)
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Brain className="w-4 h-4 text-purple-500" />
                Traitement IA
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-gray-600 space-y-2">
              <p>Tous les documents sont automatiquement :</p>
              <ul className="space-y-1 text-sm">
                <li className="flex items-center gap-2">
                  <Zap className="w-3 h-3 text-yellow-500" />
                  <strong>OCR</strong> - Texte extrait (Gemini)
                </li>
                <li className="flex items-center gap-2">
                  <Zap className="w-3 h-3 text-yellow-500" />
                  <strong>Vectorisés</strong> - Pour recherche sémantique
                </li>
                <li className="flex items-center gap-2">
                  <Zap className="w-3 h-3 text-yellow-500" />
                  <strong>Postes pricing</strong> - Extraits du BPU
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-500" />
                Format attendu
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-gray-600">
              <p className="mb-2">
                Compressez votre dossier en <strong>ZIP</strong> contenant :
              </p>
              <ul className="space-y-1 text-sm">
                <li>• RC (Règlement de Consultation)</li>
                <li>• CCTP (Cahier des Clauses)</li>
                <li>• BPU (Bordereau des Prix)</li>
                <li>• DAO complet (optionnel)</li>
              </ul>
              <p className="mt-3 text-xs text-gray-500">
                Formats supportés : PDF, Word, Excel, CSV, images
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
