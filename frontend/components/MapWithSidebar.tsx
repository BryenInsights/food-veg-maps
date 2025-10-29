"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Map from "./Map";
import { supabase } from "../lib/supabaseClient";

type Restaurant = {
  id: number;
  photo: string | null;
  nom: string;
  rating: number | null;
  latitude: number | null;
  longitude: number | null;
  menu: string | null;
  website: string | null;
  score: number | null;
};

export default function MapWithSidebar({ restaurants = [] }: { restaurants?: Restaurant[] }) {
  const [query, setQuery] = useState("");
  const [minRating, setMinRating] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [results, setResults] = useState<Restaurant[]>(restaurants);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastParamsRef = useRef<string>("");

  useEffect(() => {
    let cancelled = false;
    const key = `${query}|${minRating ?? ""}`;
    lastParamsRef.current = key;
    setLoading(true);
    setError(null);

    const timer = setTimeout(async () => {
      try {
        let q = supabase.from("restaurants").select("*");
        if (query.trim() !== "") q = q.ilike("nom", `%${query.trim()}%`);
        if (minRating !== null) q = q.gte("rating", minRating);

        const { data, error } = await q;
        if (cancelled) return;
        if (error) throw error;

        const coerced = (data ?? []).map((r: any) => ({
          ...r,
          rating: r.rating == null ? null : Number(r.rating),
          latitude: r.latitude == null ? null : Number(r.latitude),
          longitude: r.longitude == null ? null : Number(r.longitude),
          score: r.score == null ? null : Number(r.score),
        })) as Restaurant[];

        setResults(coerced);
      } catch (e: any) {
        if (!cancelled) setError(e?.message ?? "Erreur de recherche");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, minRating]);

  const filtered = useMemo(() => results, [results]);

  return (
    <div className="flex h-[calc(100vh-5rem)] gap-4">
      <aside className="w-full md:w-[360px] lg:w-[400px] shrink-0">
        <div className="h-full rounded-2xl border bg-white/70 backdrop-blur-xl supports-[backdrop-filter]:bg-white/50 flex flex-col">
          <div className="sticky top-0 z-10 p-4 border-b bg-white/70 backdrop-blur-xl rounded-t-2xl">
            <div className="text-lg font-semibold tracking-tight">Découvrir</div>
            <div className="mt-3 flex items-center gap-2">
              <div className="relative w-full">
                <input
                  placeholder="Rechercher un restaurant"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full rounded-xl border px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500/60 placeholder:text-neutral-400 bg-white/80"
                />
                <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">⌘K</div>
              </div>
              <select
                className="rounded-xl border px-3 py-2 text-sm bg-white/80"
                value={minRating ?? ""}
                onChange={(e) => setMinRating(e.target.value === "" ? null : Number(e.target.value))}
                title="Note minimale"
              >
                <option value="">Note</option>
                <option value="3">3+</option>
                <option value="3.5">3.5+</option>
                <option value="4">4+</option>
                <option value="4.5">4.5+</option>
              </select>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            {loading && (
              <div className="px-2 py-1 text-xs text-neutral-500">Recherche…</div>
            )}
            {error && (
              <div className="px-2 py-1 text-xs text-red-600">{error}</div>
            )}
            <ul className="space-y-2">
              {filtered.map((r) => (
                <li key={r.id}>
                  <button
                    onClick={() => setSelectedId(r.id)}
                    className={`group w-full text-left rounded-xl border p-3.5 transition-all bg-white/70 hover:bg-white ${
                      selectedId === r.id ? "border-emerald-600" : "border-neutral-200"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="min-w-0">
                          <div className="font-medium truncate">{r.nom}</div>
                          <div className="mt-0.5 flex items-center gap-2 text-xs text-neutral-600">
                            {r.rating !== null && <span>{Number(r.rating)}</span>}
                            {r.website && (
                              <a
                                href={r.website}
                                onClick={(e) => e.stopPropagation()}
                                target="_blank"
                                rel="noreferrer"
                                className="text-emerald-700 hover:underline"
                              >
                                Site web
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                      {r.score !== null && (
                        <span className="inline-flex h-7 items-center rounded-full bg-emerald-50 px-2.5 text-xs font-medium text-emerald-700">
                          Score {r.score}
                        </span>
                      )}
                    </div>
                  </button>
                </li>
              ))}
              {filtered.length === 0 && (
                <li className="p-3 text-sm text-neutral-500">Aucun résultat</li>
              )}
            </ul>
          </div>
        </div>
      </aside>

      <div className="flex-1">
        <div className="h-full rounded-2xl overflow-hidden border">
          <Map restaurants={filtered} selectedId={selectedId ?? undefined} />
        </div>
      </div>
    </div>
  );
}


