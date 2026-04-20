import { Button } from "@/components/ui/button";
import { Paperclip, Download } from "lucide-react";
import { useFileDownload } from "@/hooks/useFileDownload";

interface Attachment {
  id: string;
  filename: string;
  mime_type: string;
  file_size_bytes?: number;
  storage_path: string;
}

interface AttachmentListProps {
  attachments: Attachment[];
  emailId: string;
  orgSlug: string;
  className?: string;
}

export function AttachmentList({ 
  attachments, 
  emailId, 
  orgSlug,
  className = "" 
}: AttachmentListProps) {
  const { downloadEmailAttachment, downloading } = useFileDownload({ orgSlug });

  const formatBytes = (bytes?: number) => {
    if (!bytes) return "";
    if (bytes === 0) return "0 Bytes";
    
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes("pdf")) return "📄";
    if (mimeType.includes("image")) return "🖼️";
    if (mimeType.includes("word") || mimeType.includes("document")) return "📝";
    if (mimeType.includes("excel") || mimeType.includes("spreadsheet")) return "📊";
    if (mimeType.includes("zip") || mimeType.includes("compressed")) return "📦";
    return "📎";
  };

  if (attachments.length === 0) {
    return null;
  }

  return (
    <div className={`mt-4 space-y-2 ${className}`}>
      <div className="flex items-center gap-2 text-base text-gray-600">
        <Paperclip className="h-4 w-4" />
        <span>Pièces jointes ({attachments.length})</span>
      </div>
      
      <div className="space-y-2">
        {attachments.map((attachment) => (
          <div
            key={attachment.id}
            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="text-xl">{getFileIcon(attachment.mime_type)}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {attachment.filename}
                </p>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span>{attachment.mime_type}</span>
                  {attachment.file_size_bytes && (
                    <>
                      <span>•</span>
                      <span>{formatBytes(attachment.file_size_bytes)}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => downloadEmailAttachment(emailId, attachment.id)}
              disabled={downloading}
              className="ml-2"
            >
              <Download className="h-4 w-4" />
              <span className="sr-only">Télécharger</span>
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}