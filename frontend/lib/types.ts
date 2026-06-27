// TypeScript interfaces matching backend Pydantic schemas

// --- Auth ---

export interface UserCreate {
  username: string;
  password: string;
}

export interface UserLogin {
  username: string;
  password: string;
}

export interface TokenResponse {
  message: string;
  username: string;
}

// --- Words ---

export interface WordCreateRequest {
  word: string;
  meaning: string;
  synonyms?: string;
  context?: string;
  book_name: string;
  chapter_name: string;
}

export interface WordResponse {
  id: number;
  word: string;
  meaning: string;
  synonyms: string;
  context: string;
  book_name: string;
  chapter_name: string;
  date_added: string;
  mastery_level: number;
  source?: "manual" | "auto";
  rarity?: "common" | "uncommon" | "rare" | "epic" | "legendary";
}

export interface AddWordResponse {
  entry: WordResponse;
  xp_earned: number;
  new_total_xp: number;
  level_up: string | null;
  streak: number;
  achievements_unlocked: AchievementResponse[];
}

// --- Review ---

export interface ReviewAnswerRequest {
  word_id: number;
  answer: string;
}

export interface ReviewAnswerResponse {
  correct: boolean;
  correct_word: string;
  new_mastery: number;
  next_review: string;
}

export interface ReviewSessionSummary {
  correct_count: number;
  total_count: number;
  xp_earned: number;
  new_total_xp: number;
  level_up: string | null;
  streak: number;
  achievements_unlocked: AchievementResponse[];
}

// --- Profile ---

export interface ProfileResponse {
  total_xp: number;
  reader_level: string;
  current_streak: number;
  longest_streak: number;
  total_words: number;
  total_books: number;
  next_level_name: string | null;
  xp_to_next_level: number;
  current_level_threshold: number;
  next_level_threshold: number | null;
}

// --- Achievements ---

export interface AchievementResponse {
  key: string;
  emoji: string;
  title: string;
  description: string;
  earned: boolean;
  earned_at: string | null;
}

// --- WOTD ---

export interface WotdResponse {
  word: string;
  meaning: string;
  synonyms: string;
  context: string;
  book_name: string;
  chapter_name: string;
}

// --- Books ---

export interface ChapterResponse {
  name: string;
  chapter_number: number;
  word_count: number;
  earliest_entry: string | null;
  latest_entry: string | null;
}

export interface BookListItem {
  name: string;
  chapter_count: number;
  word_count: number;
}

export interface BookDetailResponse {
  name: string;
  word_count: number;
  chapter_count: number;
  chapters: ChapterResponse[];
}

// --- Dictionary ---

export interface DictionaryResult {
  word: string;
  meaning: string;
  synonyms: string;
}

// --- Review Scope ---

export interface ReviewScope {
  book?: string;
  chapter?: string;
}

// --- Gamification Event ---

export interface GamificationEvent {
  xp_earned: number;
  new_total_xp: number;
  level_up: string | null;
  achievements_unlocked: AchievementResponse[];
}

// --- Catalog / auto-import ---

export interface CatalogItem {
  gutenberg_id: number;
  title: string;
  author: string;
  subject: string;
}

export interface ImportStatus {
  gutenberg_id: number;
  state: "queued" | "fetching" | "extracting" | "done" | "error" | "unknown";
  progress: number;
  total: number;
  words: number;
  book_name: string | null;
  error: string | null;
}

export interface ChapterProgressItem {
  id: number;
  name: string;
  chapter_number: number;
  word_count: number;
  is_read: boolean;
  is_locked: boolean;
}

export interface MarkReadResponse {
  chapter_id: number;
  newly_unlocked: number;
  already_read: boolean;
  xp_earned: number;
  new_total_xp: number;
}
