"use client";

/**
 * FolderUploader - Upload d'un dossier ZIP pour création auto de candidature AO
 * 
 * Fonctionnalités:
 * - Upload de fichier ZIP contenant les documents d'un AO
 * - Analyse automatique (extraction métadonnées, OCR, vectorisation)
 * - Création automatique de la candidature
 * - Affichage du résumé des documents créés
 */

import React, { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import {
  Archive,
  Upload,
  X,
  CheckCircle2,
  Loader2,
  AlertCircle,
  FileText,
  Building2,
  Calendar,
  Euro,
  FolderOpen,
  ArrowRight,
} from "lucide-react";

interface UploadStatus {
  status: "idle" | "uploading" | "analyzing" | "creating" | "processing" | "completed" | "error";
  progress: number;
  message: string;
}

interface ExtractionResult {
  candidature_id?: string;
  candidature?: {
    id: string;
    nom_projet: string;
    client_nom?: string;
    reference_ao?: string;
    montant_total?: number;
  };
  documents_created: number;
  postes_extraits: number;
  metadata_extracted: {
    nom_projet?: string;
    client_nom?: string;
    reference_ao?: string;
    description?: string;
    date_limite_remise?: string;
    montant_total?: number;
  };
  documents_errors: Array<{
    filename: string;
    error: string;
  }>;
}

interface FolderUploaderProps {
  onSuccess?: (candidatureId: string) => void;
  className?: string;
}

export function FolderUploader({ onSuccess, className }: FolderUploaderProps) {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>({
    status: "idle",
    progress: 0,
    message: "",
  });
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      validateAndSetFile(droppedFiles[0]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  }, []);

  const validateAndSetFile = (file: File) => {
    // Vérifier que c'est un ZIP
    if (!file.name.endsWith('.zip')) {
      setStatus({
        status: "error",
        progress: 0,
        message: "Le fichier doit être un fichier ZIP",
      });
      return;
    }

    // Vérifier la taille (max 500 MB)
    if (file.size > 500 * 1024 * 1024) {
      setStatus({
        status: "error",
        progress: 0,
        message: "Fichier trop volumineux (max 500 MB)",
      });
      return;
    }

    setFile(file);
    setStatus({ status: "idle", progress: 0, message: "" });
    setResult(null);
  };

  const handleUpload = async () => {
    if (!file) return;

    setStatus({
      status: "uploading",
      progress: 10,
      message: "Upload du ZIP en cours...",
    });

    try {
      const formData = new FormData();
      formData.append("folder_zip", file);

      // Upload
      setStatus({
        status: "uploading",
        progress: 30,
        message: "Envoi du fichier...",
      });

      const response = await fetch("/api/v1/ao/upload-folder", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Erreur lors du traitement");
      }

      const data: ExtractionResult = await response.json();
      setResult(data);

      setStatus({
        status: "completed",
        progress: 100,
        message: "Candidature créée avec succès !",
      });

      // Callback
      if (data.candidature_id) {
        onSuccess?.(data.candidature_id);
      }
    } catch (error) {
      setStatus({
        status: "error",
        progress: 0,
        message: error instanceof Error ? error.message : "Erreur inconnue",
      });
    }
  };

  const clearFile = () => {
    setFile(null);
    setResult(null);
    setStatus({ status: "idle", progress: 0, message: "" });
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatMontant = (montant?: number) => {
    if (!montant) return "Non détecté";
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }).format(montant);
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Zone de drop */}
      {!file && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all",
            isDragging
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            onChange={handleFileSelect}
            className="hidden"
          />
          <Archive className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Déposez votre dossier AO (ZIP)
          </h3>
          <p className="text-sm text-gray-500 mb-2">
            ou cliquez pour sélectionner un fichier
          </p>
          <p className="text-xs text-gray-400">
            Le ZIP doit contenir les documents (RC, CCTP, BPU, etc.)
            <br />
            Taille maximale : 500 MB
          </p>
        </div>
      )}

      {/* Fichier sélectionné */}
      {file && status.status !== "completed" && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Archive className="w-8 h-8 text-blue-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-lg">{file.name}</h4>
                <p className="text-sm text-gray-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>

                {/* Barre de progression */}
                {status.status !== "idle" && status.status !== "error" && (
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-gray-600">{status.message}</span>
                      <span className="font-medium">{status.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div
                        className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                        style={{ width: `${status.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Message d'erreur */}
                {status.status === "error" && (
                  <Alert variant="destructive" className="mt-4">
                    <AlertCircle className="w-4 h-4" />
                    <AlertDescription>{status.message}</AlertDescription>
                  </Alert>
                )}
              </div>
              {status.status === "idle" && (
                <Button variant="ghost" size="icon" onClick={clearFile}>
                  <X className="w-5 h-5" />
                </Button>
              )}
            </div>

            {/* Bouton lancer */}
            {status.status === "idle" && (
              <div className="mt-6 flex gap-3">
                <Button variant="outline" onClick={clearFile} className="flex-1">
                  Annuler
                </Button>
                <Button onClick={handleUpload} className="flex-1">
                  <Upload className="w-4 h-4 mr-2" />
                  Analyser et créer
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Résultat */}
      {result && status.status === "completed" && (
        <Card className="border-green-200 bg-green-50/50">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-full">
                <CheckCircle2 className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <CardTitle className="text-green-900">
                  Candidature créée avec succès !
                </CardTitle>
                <p className="text-sm text-green-700">
                  {result.documents_created} documents analysés et traités
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Infos extraites */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white p-4 rounded-lg border">
                <div className="flex items-center gap-2 text-gray-500 mb-1">
                  <FolderOpen className="w-4 h-4" />
                  <span className="text-sm">Projet</span>
                </div>
                <p className="font-semibold">
                  {result.metadata_extracted.nom_projet || result.candidature?.nom_projet}
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border">
                <div className="flex items-center gap-2 text-gray-500 mb-1">
                  <Building2 className="w-4 h-4" />
                  <span className="text-sm">Client</span>
                </div>
                <p className="font-semibold">
                  {result.metadata_extracted.client_nom || "Non détecté"}
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border">
                <div className="flex items-center gap-2 text-gray-500 mb-1">
                  <FileText className="w-4 h-4" />
                  <span className="text-sm">Référence</span>
                </div>
                <p className="font-semibold">
                  {result.metadata_extracted.reference_ao || "Non détecté"}
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border">
                <div className="flex items-center gap-2 text-gray-500 mb-1">
                  <Euro className="w-4 h-4" />
                  <span className="text-sm">Montant total</span>
                </div>
                <p className="font-semibold">
                  {formatMontant(result.metadata_extracted.montant_total)}
                </p>
              </div>
            </div>

            {/* Stats */}
            <div className="flex gap-3">
              <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                <FileText className="w-3 h-3 mr-1" />
                {result.documents_created} documents
              </Badge>
              {result.postes_extraits > 0 && (
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  <Archive className="w-3 h-3 mr-1" />
                  {result.postes_extraits} postes pricing
                </Badge>
              )}
            </div>

            {/* Erreurs si présentes */}
            {result.documents_errors.length > 0 && (
              <Alert>
                <AlertCircle className="w-4 h-4" />
                <AlertDescription>
                  {result.documents_errors.length} document(s) n'ont pas pu être traités
                </AlertDescription>
              </Alert>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <Button variant="outline" onClick={clearFile} className="flex-1">
                Importer un autre dossier
              </Button>
              {result.candidature_id && (
                <Button
                  onClick={() => router.push(`/dashboard/ao/${result.candidature_id}`)}
                  className="flex-1"
                >
                  Voir la candidature
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
