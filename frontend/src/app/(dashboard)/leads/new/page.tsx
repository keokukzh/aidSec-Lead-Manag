"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { leadsApi } from "@/lib/api";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import Link from "next/link";

export default function NewLeadPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    firma: "",
    name: "",
    email: "",
    telefon: "",
    kategorie: "anwalt",
    status: "offen",
    notizen: "",
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => leadsApi.create(data),
    onSuccess: () => {
      router.push("/leads");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/leads"
          className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#2a3040] text-[#b8bec6] hover:bg-[#00d4aa22] hover:text-[#00d4aa]"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">Neuer Lead</h1>
          <p className="text-[#b8bec6]">Lead erstellen</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Main Info */}
        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
          <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">
            Lead-Informationen
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm text-[#b8bec6]">Firma *</label>
              <input
                type="text"
                required
                value={formData.firma}
                onChange={(e) =>
                  setFormData({ ...formData, firma: e.target.value })
                }
                className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-[#b8bec6]">Name *</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-[#b8bec6]">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-[#b8bec6]">Telefon</label>
              <input
                type="tel"
                value={formData.telefon}
                onChange={(e) =>
                  setFormData({ ...formData, telefon: e.target.value })
                }
                className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Status & Category */}
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
            <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">Status</h2>
            <select
              value={formData.status}
              onChange={(e) =>
                setFormData({ ...formData, status: e.target.value })
              }
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
            >
              <option value="offen">Offen</option>
              <option value="pending">Pending</option>
              <option value="gewonnen">Gewonnen</option>
              <option value="verloren">Verloren</option>
            </select>
          </div>

          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
            <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">
              Kategorie
            </h2>
            <select
              value={formData.kategorie}
              onChange={(e) =>
                setFormData({ ...formData, kategorie: e.target.value })
              }
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
            >
              <option value="anwalt">Anwalt</option>
              <option value="praxis">Praxis</option>
              <option value="wordpress">WordPress</option>
            </select>
          </div>
        </div>

        {/* Notes */}
        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
          <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">Notizen</h2>
          <textarea
            value={formData.notizen}
            onChange={(e) =>
              setFormData({ ...formData, notizen: e.target.value })
            }
            rows={4}
            className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
            placeholder="Notizen zum Lead..."
          />
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <Link
            href="/leads"
            className="rounded-md border border-[#2a3040] px-4 py-2 text-[#e8eaed] hover:bg-[#2a3040]"
          >
            Abbrechen
          </Link>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-6 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
          >
            {createMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Erstellen
          </button>
        </div>
      </form>
    </div>
  );
}
