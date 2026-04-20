"use client";

/**
 * DocumentUploader - Composant d'upload de documents pour AO
 * 
 * Fonctionnalités:
 * - Drag & drop de fichiers
 * - Upload multiple
 * - Progression du traitement (OCR + Vectorisation)
 * - Bouton "Charger depuis documents" (sélection fichier)
 */

import React, { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Upload,
  FileText,
  X,
  CheckCircle2,
  Loader2,
  AlertCircle,
  File,
  Image as ImageIcon,
  Table,
} from "lucide-react";

interface UploadFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  status: "pending" | "uploading" | "processing" | "completed" | "error";
  progress: number;
  result?: {
    document_id?: string;
    text_length?: number;
    chunks_created?: number;
  };
  error?: string;
}

interface DocumentUploaderProps {
  candidatureId: string;
  onUploadComplete?: () => void;
  className?: string;
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

const getFileIcon = (type: string) => {
  if (type.includes("pdf")) return <FileText className="w-5 h-5 text-red-500" />;
  if (type.includes("image")) return <ImageIcon className="w-5 h-5 text-blue-500" />;
  if (type.includes("sheet") || type.includes("excel") || type.includes("csv"))
    return <Table className="w-5 h-5 text-green-500" />;
  return <File className="w-5 h-5 text-gray-500" />;
};

export function DocumentUploader({
  candidatureId,
  onUploadComplete,
  className,
}: DocumentUploaderProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
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
    addFiles(droppedFiles);
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = Array.from(e.target.files || []);
      addFiles(selectedFiles);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    []
  );

  const addFiles = (newFiles: File[]) => {
    const uploadFiles: UploadFile[] = newFiles.map((file) => ({
      id: Math.random().toString(36).substring(7),
      file,
      name: file.name,
      size: file.size,
      type: file.type,
      status: "pending",
      progress: 0,
    }));

    setFiles((prev) => [...prev, ...uploadFiles]);

    // Lancer l'upload automatiquement
    uploadFiles.forEach((uploadFile) => {
      uploadFileAsync(uploadFile);
    });
  };

  const uploadFileAsync = async (uploadFile: UploadFile) => {
    // Mettre à jour le statut
    setFiles((prev) =>
      prev.map((f) =>
        f.id === uploadFile.id ? { ...f, status: "uploading", progress: 10 } : f
      )
    );

    try {
      const formData = new FormData();
      formData.append("file", uploadFile.file);
      formData.append("process_ocr", "true");
      formData.append("vectorize", "true");

      // Upload
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id ? { ...f, progress: 30 } : f
        )
      );

      const response = await fetch(
        `/api/v1/ao/candidatures/${candidatureId}/documents/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Erreur d'upload");
      }

      const result = await response.json();

      // Mise à jour avec succès
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? {
                ...f,
                status: "completed",
                progress: 100,
                result: {
                  document_id: result.document_id,
                  text_length: result.text_length,
                  chunks_created: result.chunks_created,
                },
              }
            : f
        )
      );

      // Callback
      onUploadComplete?.();
    } catch (error) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? {
                ...f,
                status: "error",
                progress: 0,
                error: error instanceof Error ? error.message : "Erreur inconnue",
              }
            : f
        )
      );
    }
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const clearCompleted = () => {
    setFiles((prev) => prev.filter((f) => f.status !== "completed"));
  };

  const retryFile = (id: string) => {
    const file = files.find((f) => f.id === id);
    if (file) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === id ? { ...f, status: "pending", progress: 0, error: undefined } : f
        )
      );
      uploadFileAsync(file);
    }
  };

  const completedCount = files.filter((f) => f.status === "completed").length;
  const errorCount = files.filter((f) => f.status === "error").length;
  const processingCount = files.filter(
    (f) => f.status === "uploading" || f.status === "processing"
  ).length;

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Charger des documents
          </CardTitle>
          {completedCount > 0 && (
            <Button variant="ghost" size="sm" onClick={clearCompleted}>
              Effacer terminés
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Zone de drop */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
            isDragging
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.png,.jpg,.jpeg"
            onChange={handleFileSelect}
            className="hidden"
          />
          <Upload className="w-10 h-10 mx-auto mb-3 text-gray-400" />
          <p className="text-sm font-medium text-gray-700">
            Glissez-déposez vos fichiers ici
          </p>
          <p className="text-xs text-gray-500 mt-1">
            ou cliquez pour sélectionner
          </p>
          <p className="text-xs text-gray-400 mt-2">
            PDF, Word, Excel, Images (max 50MB)
          </p>
        </div>

        {/* Statistiques */}
        {files.length > 0 && (
          <div className="flex gap-4 text-sm">
            <Badge variant="outline" className="bg-green-50">
              <CheckCircle2 className="w-3 h-3 mr-1 text-green-600" />
              {completedCount} terminé(s)
            </Badge>
            {processingCount > 0 && (
              <Badge variant="outline" className="bg-blue-50">
                <Loader2 className="w-3 h-3 mr-1 text-blue-600 animate-spin" />
                {processingCount} en cours
              </Badge>
            )}
            {errorCount > 0 && (
              <Badge variant="outline" className="bg-red-50">
                <AlertCircle className="w-3 h-3 mr-1 text-red-600" />
                {errorCount} erreur(s)
              </Badge>
            )}
          </div>
        )}

        {/* Liste des fichiers */}
        {files.length > 0 && (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {files.map((file) => (
              <div
                key={file.id}
                className={cn(
                  "flex items-center gap-3 p-3 rounded-lg border",
                  file.status === "completed" && "bg-green-50 border-green-200",
                  file.status === "error" && "bg-red-50 border-red-200",
                  file.status === "uploading" && "bg-blue-50 border-blue-200"
                )}
              >
                {getFileIcon(file.type)}

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(file.size)}
                    {file.result?.text_length !== undefined && (
                      <span className="ml-2">
                        • {file.result.text_length} caractères
                      </span>
                    )}
                    {file.result?.chunks_created !== undefined && (
                      <span className="ml-2">
                        • {file.result.chunks_created} chunks
                      </span>
                    )}
                  </p>

                  {/* Barre de progression */}
                  {(file.status === "uploading" || file.status === "processing") && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-blue-600 h-1.5 rounded-full transition-all"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        {file.progress < 30 && "Upload..."}
                        {file.progress >= 30 && file.progress < 60 && "OCR en cours..."}
                        {file.progress >= 60 && file.progress < 100 && "Vectorisation..."}
                      </p>
                    </div>
                  )}

                  {/* Message d'erreur */}
                  {file.status === "error" && file.error && (
                    <p className="text-xs text-red-600 mt-1">{file.error}</p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  {file.status === "completed" && (
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                  )}

                  {file.status === "error" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => retryFile(file.id)}
                    >
                      Réessayer
                    </Button>
                  )}

                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => removeFile(file.id)}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
