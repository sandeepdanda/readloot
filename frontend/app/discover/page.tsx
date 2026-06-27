"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Sparkles, BookOpen, Loader2, Check } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import * as api from "@/lib/api";
import type { ImportStatus } from "@/lib/types";

const EXAMPLES = ["Sherlock Holmes", "Austen", "Frankenstein", "Alice"];

export default function DiscoverPage() {
  const [query, setQuery] = useState("");
  const [importing, setImporting] = useState<number | null>(null);
  const [status, setStatus] = useState<ImportStatus | null>(null);
  const router = useRouter();
  const qc = useQueryClient();

  const catalog = useQuery({
    queryKey: ["catalog", query],
    queryFn: () => api.searchCatalog(query),
  });

  // Poll import status until done/error.
  function pollStatus(gid: number) {
    const tick = async () => {
      try {
        const s = await api.getImportStatus(gid);
        setStatus(s);
        if (s.state === "done") {
          setImporting(null);
          qc.invalidateQueries({ queryKey: ["books"] });
          if (s.book_name) {
            router.push(`/library/${encodeURIComponent(s.book_name)}`);
          }
          return;
        }
        if (s.state === "error") {
          setImporting(null);
          return;
        }
        setTimeout(tick, 500);
      } catch {
        setImporting(null);
      }
    };
    tick();
  }

  const startImport = useMutation({
    mutationFn: (gid: number) => api.importBook(gid),
    onMutate: (gid) => {
      setImporting(gid);
      setStatus(null);
    },
    onSuccess: (_data, gid) => pollStatus(gid),
    onError: () => setImporting(null),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Sparkles className="h-7 w-7 text-primary" /> Discover books
        </h1>
        <p className="text-muted-foreground mt-1">
          Import a public-domain book and we&apos;ll pick the words worth learning,
          chapter by chapter.
        </p>
      </div>

      <Input
        placeholder="Search by title or author…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="h-11 max-w-xl"
        aria-label="Search the book catalog"
      />

      {/* Empty-query onboarding: example chips */}
      {query.length === 0 && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>Try:</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setQuery(ex)}
              className="rounded-full border border-border px-3 py-1 transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      {catalog.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      )}

      {catalog.data && catalog.data.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center py-12 text-center">
            <BookOpen className="mb-3 h-10 w-10 text-muted-foreground" />
            <p className="font-medium">No books match “{query}”.</p>
            <p className="text-sm text-muted-foreground">
              Try a broader term, or an author&apos;s last name.
            </p>
          </CardContent>
        </Card>
      )}

      {catalog.data && catalog.data.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {catalog.data.map((book) => {
            const isThis = importing === book.gutenberg_id;
            return (
              <Card key={book.gutenberg_id} className="flex flex-col">
                <CardContent className="flex flex-1 flex-col gap-1 p-5">
                  <h3 className="font-semibold leading-snug">{book.title}</h3>
                  <p className="text-sm text-muted-foreground">{book.author}</p>
                  <span className="mt-1 inline-flex w-fit rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                    {book.subject}
                  </span>

                  {isThis && status ? (
                    <div className="mt-auto pt-4">
                      <div className="flex items-center gap-2 text-sm text-primary">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {status.state === "fetching" && "Fetching text…"}
                        {status.state === "extracting" &&
                          `Extracting… ${status.progress}/${status.total} chapters`}
                        {status.state === "queued" && "Queued…"}
                      </div>
                      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{
                            width: status.total
                              ? `${(status.progress / status.total) * 100}%`
                              : "10%",
                          }}
                        />
                      </div>
                      {status.state === "error" && (
                        <p className="mt-2 text-xs text-destructive">
                          Import failed: {status.error}
                        </p>
                      )}
                    </div>
                  ) : (
                    <Button
                      className="mt-auto"
                      size="sm"
                      disabled={importing !== null}
                      onClick={() => startImport.mutate(book.gutenberg_id)}
                    >
                      {importing !== null ? (
                        <>
                          <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> Working…
                        </>
                      ) : (
                        <>
                          <Sparkles className="mr-1.5 h-4 w-4" /> Import
                        </>
                      )}
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
