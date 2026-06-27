"use client";

import { useState, use } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import * as api from "@/lib/api";

export default function BookDetailPage({
  params,
}: {
  params: Promise<{ name: string }> | { name: string };
}) {
  // Next 14.2 passes params as a plain object; Next 15 as a Promise. Support both.
  const resolved =
    typeof (params as Promise<{ name: string }>).then === "function"
      ? use(params as Promise<{ name: string }>)
      : (params as { name: string });
  const bookName = decodeURIComponent(resolved.name);
  const [expandedChapter, setExpandedChapter] = useState<number | null>(null);

  const book = useQuery({
    queryKey: ["book", bookName],
    queryFn: () => api.getBookDetails(bookName),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/books">
          <Button variant="ghost" size="sm">
            ← Back
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{bookName}</h1>
          {book.data && (
            <p className="text-muted-foreground mt-1">
              {book.data.chapter_count} chapter
              {book.data.chapter_count !== 1 ? "s" : ""} ·{" "}
              {book.data.word_count} word{book.data.word_count !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        <Link href={`/library/${encodeURIComponent(bookName)}`}>
          <Button variant="outline" size="sm">Chapters &amp; unlocks</Button>
        </Link>
      </div>

      {book.isLoading && (
        <p className="text-muted-foreground">Loading chapters...</p>
      )}

      {book.isError && (
        String(book.error?.message).includes("404") ? (
          <div className="text-center py-12">
            <p className="text-destructive mb-4">Book not found</p>
            <Link href="/books" className="text-primary underline">Back to books</Link>
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-destructive mb-4">Failed to load book</p>
            <button onClick={() => book.refetch()} className="text-primary underline">Try again</button>
          </div>
        )
      )}

      {book.data && (
        <div className="space-y-3">
          {book.data.chapters.map((chapter) => (
            <Card
              key={chapter.chapter_number}
              className="cursor-pointer transition-colors hover:bg-muted/50"
              onClick={() =>
                setExpandedChapter(
                  expandedChapter === chapter.chapter_number
                    ? null
                    : chapter.chapter_number,
                )
              }
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center justify-between">
                  <span>
                    Chapter {chapter.chapter_number}: {chapter.name}
                  </span>
                  <span className="text-muted-foreground text-sm">
                    {expandedChapter === chapter.chapter_number ? "▲" : "▼"}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                  <span>
                    📝 {chapter.word_count} word
                    {chapter.word_count !== 1 ? "s" : ""}
                  </span>
                  {chapter.earliest_entry && (
                    <span>
                      📅 {chapter.earliest_entry}
                      {chapter.latest_entry &&
                      chapter.latest_entry !== chapter.earliest_entry
                        ? ` – ${chapter.latest_entry}`
                        : ""}
                    </span>
                  )}
                </div>
                {expandedChapter === chapter.chapter_number && (
                  <div className="mt-4 pt-3 border-t text-sm space-y-2">
                    <div className="grid grid-cols-2 gap-2 text-muted-foreground">
                      <span>First entry:</span>
                      <span>{chapter.earliest_entry || "—"}</span>
                      <span>Latest entry:</span>
                      <span>{chapter.latest_entry || "—"}</span>
                      <span>Total words:</span>
                      <span>{chapter.word_count}</span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
