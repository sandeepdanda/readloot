// Small, restrained word-card adornments for Phase 2 (rarity + evolution).
//
// Rarity is a genre-standard color ramp (common=gray ... legendary=gold) shown
// as a tiny gem; only legendary gets a soft glow so it never out-weighs the
// word. Evolution is a growth glyph derived from mastery_level (0-5). Both are
// reduced-motion-safe: the only animation is the legendary pulse, gated behind
// motion-safe so it's static when the user prefers reduced motion.

import { cn } from "@/lib/utils";
import type { WordResponse } from "@/lib/types";

type Rarity = NonNullable<WordResponse["rarity"]>;

// Literal class strings (no runtime concatenation) so Tailwind's content
// scanner keeps them — no safelist needed.
const RARITY_STYLES: Record<Rarity, { dot: string; label: string }> = {
  common: { dot: "bg-zinc-400", label: "text-zinc-400" },
  uncommon: { dot: "bg-green-500", label: "text-green-500" },
  rare: { dot: "bg-sky-500", label: "text-sky-500" },
  epic: { dot: "bg-purple-500", label: "text-purple-500" },
  legendary: {
    dot: "bg-amber-400 shadow-[0_0_6px_1px] shadow-amber-400/60 motion-safe:animate-pulse",
    label: "text-amber-400",
  },
};

// mastery_level (0-5) -> growth stage. Mirrors evolution_stage() in
// src/readloot/vocab_extractor.py; kept on the frontend since it's a pure
// presentational mapping off a field the response already carries.
const EVOLUTION_STAGES: { glyph: string; name: string }[] = [
  { glyph: "🌱", name: "Seed" },
  { glyph: "🌿", name: "Sprout" },
  { glyph: "🪴", name: "Sapling" },
  { glyph: "🌳", name: "Tree" },
  { glyph: "🌲", name: "Ancient Oak" },
  { glyph: "💎", name: "Crystal Tree" },
];

export function evolutionStage(masteryLevel: number) {
  const idx = Math.max(0, Math.min(masteryLevel, EVOLUTION_STAGES.length - 1));
  return EVOLUTION_STAGES[idx];
}

export function RarityGem({ rarity = "common" }: { rarity?: Rarity }) {
  const style = RARITY_STYLES[rarity] ?? RARITY_STYLES.common;
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-medium capitalize"
      title={`${rarity} rarity`}
    >
      <span className={cn("h-2 w-2 rounded-full", style.dot)} aria-hidden />
      <span className={style.label}>{rarity}</span>
    </span>
  );
}

export function EvolutionGlyph({ masteryLevel }: { masteryLevel: number }) {
  const stage = evolutionStage(masteryLevel);
  return (
    <span className="text-sm" title={`${stage.name} (mastery ${masteryLevel}/5)`}>
      {stage.glyph}
    </span>
  );
}
