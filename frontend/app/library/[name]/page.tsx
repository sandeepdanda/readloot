"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion, MotionConfig } from "framer-motion";
import Link from "next/link";
import { Lock, BookOpen, Check, Sparkles } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import * as api from "@/lib/api";
import type { ChapterProgressItem } from "@/lib/types";

export default function LibraryBookPage({
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
  const qc = useQueryClient();
  const [xpBurst, setXpBurst] = useState<{ id: number; amount: number } | null>(
    null,
  );

  const chapters = useQuery({
    queryKey: ["chapters", bookName],
    queryFn: () => api.getBookChapters(bookName),
  });

  const markRead = useMutation({
    mutationFn: (chapterId: number) => api.markChapterRead(chapterId),
    onSuccess: (res) => {
      if (res.xp_earned > 0) {
        setXpBurst({ id: res.chapter_id, amount: res.xp_earned });
        setTimeout(() => setXpBurst(null), 1200);
      }
      qc.invalidateQueries({ queryKey: ["chapters", bookName] });
      qc.invalidateQueries({ queryKey: ["profile"] });
    },
  });

  const data = chapters.data ?? [];
  const readCount = data.filter((c) => c.is_read).length;
  const allRead = data.length > 0 && readCount === data.length;
  // The first not-yet-read chapter is the single bright "current" row.
  const currentId = data.find((c) => !c.is_read)?.id ?? null;

  return (
    <MotionConfig reducedMotion="user">
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Link href="/discover">
            <Button variant="ghost" size="sm">← Discover</Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">{bookName}</h1>
            <p className="mt-1 text-muted-foreground">
              {readCount}/{data.length} chapters read
            </p>
          </div>
        </div>

        {/* Freshly-imported empty-ish state: teach the unlock mechanic inline */}
        {data.length > 0 && readCount === 0 && (
          <Card className="border-dashed p-6 text-center">
            <BookOpen className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
            <p className="font-medium">Your loot is locked inside the chapters.</p>
            <p className="text-sm text-muted-foreground">
              Read a chapter, mark it complete, and its words drop into your
              review queue.
            </p>
          </Card>
        )}

        {allRead && (
          <Card className="border-primary/40 bg-primary/5 p-4 text-center">
            <p className="font-medium text-primary">
              🎉 Whole book unlocked — every word is in your review queue.
            </p>
          </Card>
        )}

        {chapters.isLoading && (
          <p className="text-muted-foreground">Loading chapters…</p>
        )}

        <ul className="space-y-3">
          {data.map((ch) => (
            <ChapterRow
              key={ch.id}
              chapter={ch}
              isCurrent={ch.id === currentId}
              busy={markRead.isPending}
              xpBurst={xpBurst?.id === ch.id ? xpBurst.amount : null}
              onMarkRead={() => markRead.mutate(ch.id)}
            />
          ))}
        </ul>
      </div>
    </MotionConfig>
  );
}

function ChapterRow({
  chapter,
  isCurrent,
  busy,
  xpBurst,
  onMarkRead,
}: {
  chapter: ChapterProgressItem;
  isCurrent: boolean;
  busy: boolean;
  xpBurst: number | null;
  onMarkRead: () => void;
}) {
  const status = chapter.is_read ? "done" : isCurrent ? "current" : "locked";

  return (
    <motion.li
      layout
      className={[
        "relative flex items-center gap-3 rounded-2xl border p-4 transition-colors",
        status === "done" &&
          "border-transparent bg-muted/40 text-muted-foreground",
        status === "current" &&
          "border-primary/40 bg-card shadow-sm ring-1 ring-primary/30",
        status === "locked" && "border-border/60 bg-card/50 opacity-60",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={status}
          initial={{ scale: 0.6, opacity: 0, rotate: -12 }}
          animate={{ scale: 1, opacity: 1, rotate: 0 }}
          exit={{ scale: 0.6, opacity: 0 }}
          transition={{ type: "spring", visualDuration: 0.35, bounce: 0.2 }}
          className="shrink-0"
        >
          {status === "done" ? (
            <Check className="h-5 w-5 text-primary" />
          ) : status === "current" ? (
            <BookOpen className="h-5 w-5 text-primary" />
          ) : (
            <Lock className="h-5 w-5 text-muted-foreground" />
          )}
        </motion.span>
      </AnimatePresence>

      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">
          Chapter {chapter.chapter_number}: {chapter.name}
        </p>
        <p className="text-xs text-muted-foreground">
          <Sparkles className="mr-1 inline h-3 w-3" />
          {chapter.word_count} suggested word
          {chapter.word_count !== 1 ? "s" : ""}
        </p>
      </div>

      {status === "current" && (
        <Button size="sm" disabled={busy} onClick={onMarkRead}>
          Mark as read
        </Button>
      )}
      {status === "locked" && (
        <span className="text-xs text-muted-foreground">
          Read Ch. {chapter.chapter_number - 1} to unlock
        </span>
      )}

      {/* XP burst on unlock */}
      <AnimatePresence>
        {xpBurst !== null && (
          <motion.span
            initial={{ opacity: 0, y: 0, scale: 0.8 }}
            animate={{ opacity: 1, y: -18, scale: 1 }}
            exit={{ opacity: 0, y: -28 }}
            transition={{ duration: 0.5 }}
            className="absolute right-4 top-2 rounded-full bg-primary/15 px-2 py-0.5 text-xs font-semibold text-primary"
          >
            +{xpBurst} XP
          </motion.span>
        )}
      </AnimatePresence>
    </motion.li>
  );
}
