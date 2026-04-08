"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import * as api from "@/lib/api";

const LEVEL_COLORS: Record<string, string> = {
  Novice: "text-muted-foreground",
  "Page Turner": "text-blue-500",
  Bookworm: "text-green-500",
  "Word Smith": "text-purple-500",
  "Lexicon Lord": "text-yellow-500",
  "ReadLoot Master": "text-red-500",
};

export default function StatsPage() {
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: api.getProfile,
  });

  if (profile.isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Stats</h1>
        <p className="text-muted-foreground">Loading stats...</p>
      </div>
    );
  }

  const data = profile.data;
  if (!data) return null;

  const isMaxLevel = !data.next_level_threshold;
  const xpInLevel = data.total_xp - data.current_level_threshold;
  const xpRange = data.next_level_threshold
    ? data.next_level_threshold - data.current_level_threshold
    : 1;
  const progressPercent = isMaxLevel
    ? 100
    : Math.min(100, (xpInLevel / xpRange) * 100);

  const levelColor = LEVEL_COLORS[data.reader_level] || "text-primary";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Stats</h1>
        <p className="text-muted-foreground mt-1">Your profile and progress</p>
      </div>

      {/* Reader Level */}
      <Card>
        <CardContent className="pt-6 text-center space-y-4">
          <p className={`text-4xl font-bold ${levelColor}`}>
            {data.reader_level}
          </p>
          <p className="text-lg font-semibold">{data.total_xp} XP</p>

          {isMaxLevel ? (
            <div className="rounded-lg bg-secondary/10 border border-secondary/30 p-3">
              <p className="font-semibold text-secondary-foreground">
                🏆 Max level reached!
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <Progress value={progressPercent} />
              <p className="text-xs text-muted-foreground">
                {data.xp_to_next_level} XP to {data.next_level_name}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Current Streak
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {data.current_streak}
              {data.current_streak >= 2 && " 🔥"}
            </p>
            <p className="text-xs text-muted-foreground">days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Longest Streak
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{data.longest_streak}</p>
            <p className="text-xs text-muted-foreground">days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Total XP
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-primary">{data.total_xp}</p>
            <p className="text-xs text-muted-foreground">experience</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Total Words
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{data.total_words}</p>
            <p className="text-xs text-muted-foreground">in vault</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Total Books
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{data.total_books}</p>
            <p className="text-xs text-muted-foreground">in library</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
