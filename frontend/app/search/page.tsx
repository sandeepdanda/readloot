"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RarityGem, EvolutionGlyph } from "@/components/word-badges";
import * as api from "@/lib/api";
import type { WordResponse } from "@/lib/types";

const PAGE_SIZE = 20;

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<WordResponse[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [displayCount, setDisplayCount] = useState(PAGE_SIZE);

  const doSearch = async (searchQuery: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchWords(searchQuery);
      setResults(data);
      setSearched(true);
      setDisplayCount(PAGE_SIZE);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setSearched(false);
      setError(null);
      return;
    }

    const timer = setTimeout(() => doSearch(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Search</h1>
        <p className="text-muted-foreground mt-1">
          Search your word collection
        </p>
      </div>

      <Input
        placeholder="Search words, meanings, context..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="text-lg h-12"
        autoFocus
      />

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="animate-pulse bg-muted rounded-lg h-28" />
          ))}
        </div>
      )}

      {!query.trim() && !searched && (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <span className="text-5xl mb-4">🔍</span>
            <p className="text-muted-foreground">
              Search your vault by word, meaning, or context
            </p>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <span className="text-5xl mb-4">⚠️</span>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button variant="outline" onClick={() => doSearch(query.trim())}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {searched && !error && results.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <span className="text-5xl mb-4">🤷</span>
            <p className="text-muted-foreground">
              No words found for &ldquo;{query}&rdquo;
            </p>
          </CardContent>
        </Card>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Showing {Math.min(displayCount, results.length)} of {results.length} result{results.length !== 1 ? "s" : ""}
          </p>
          {results.slice(0, displayCount).map((word) => (
            <Card key={`${word.id}-${word.book_name}`}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-lg text-primary">
                    {word.word}
                    <RarityGem rarity={word.rarity} />
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                      {word.source === "auto" ? "✨ Suggested" : "🔖 Saved"}
                    </span>
                    <Badge variant="outline" className="gap-1">
                      <EvolutionGlyph masteryLevel={word.mastery_level} />
                      Mastery {word.mastery_level}/5
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm">{word.meaning}</p>
                {word.context && (
                  <blockquote className="border-l-2 border-primary/30 pl-3 text-sm italic text-muted-foreground">
                    {word.context}
                  </blockquote>
                )}
                <p className="text-xs text-muted-foreground">
                  📖 {word.book_name} / {word.chapter_name}
                </p>
              </CardContent>
            </Card>
          ))}
          {displayCount < results.length && (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => setDisplayCount((c) => c + PAGE_SIZE)}
            >
              Show more
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
