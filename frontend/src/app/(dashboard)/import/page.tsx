"use client";

import { useState, useRef } from "react";
import { importExportApi } from "@/lib/api";
import { Upload, Download, Loader2, FileSpreadsheet, AlertCircle } from "lucide-react";

export default function ImportPage() {
  const [isImporting, setIsImporting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsImporting(true);
    setMessage(null);

    try {
      const result = await importExportApi.importExcel(file);
      setMessage({
        type: "success",
        text: `Erfolgreich ${result.imported || 0} Leads importiert`,
      });
    } catch (error: any) {
      setMessage({
        type: "error",
        text: error.message || "Import fehlgeschlagen",
      });
    } finally {
      setIsImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleExport = () => {
    importExportApi.exportExcel();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#e8eaed]">Import / Export</h1>
        <p className="text-[#b8bec6]">Excel-Dateien verarbeiten</p>
      </div>

      {/* Import Section */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <div className="mb-4 flex items-center gap-2">
          <Upload className="h-5 w-5 text-[#00d4aa]" />
          <h2 className="text-lg font-semibold text-[#e8eaed]">Import</h2>
        </div>

        <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-[#2a3040] p-8">
          <FileSpreadsheet className="mb-4 h-12 w-12 text-[#b8bec6]" />
          <p className="mb-2 text-[#e8eaed]">
            Excel-Datei hier ablegen oder klicken zum Auswählen
          </p>
          <p className="mb-4 text-sm text-[#6b728099]">
            Unterstützte Formate: .xlsx, .xls
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleImport}
            disabled={isImporting}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="flex cursor-pointer items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
          >
            {isImporting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Importiere...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Datei auswählen
              </>
            )}
          </label>
        </div>

        {message && (
          <div
            className={`mt-4 flex items-center gap-2 rounded-lg p-4 ${
              message.type === "success"
                ? "bg-[#2ecc7133] text-[#2ecc71]"
                : "bg-[#e74c3c33] text-[#e74c3c]"
            }`}
          >
            {message.type === "error" && <AlertCircle className="h-5 w-5" />}
            {message.text}
          </div>
        )}
      </div>

      {/* Export Section */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <div className="mb-4 flex items-center gap-2">
          <Download className="h-5 w-5 text-[#00d4aa]" />
          <h2 className="text-lg font-semibold text-[#e8eaed]">Export</h2>
        </div>

        <p className="mb-4 text-[#b8bec6]">
          Alle Leads als Excel-Datei herunterladen
        </p>

        <button
          onClick={handleExport}
          className="flex items-center gap-2 rounded-md border border-[#2a3040] px-4 py-2 text-[#e8eaed] hover:bg-[#00d4aa22]"
        >
          <Download className="h-4 w-4" />
          Alle Leads exportieren
        </button>
      </div>
    </div>
  );
}
