import type {
  UserCreate,
  UserLogin,
  TokenResponse,
  WordCreateRequest,
  WordResponse,
  AddWordResponse,
  ReviewAnswerResponse,
  ReviewSessionSummary,
  ProfileResponse,
  AchievementResponse,
  WotdResponse,
  BookListItem,
  BookDetailResponse,
  DictionaryResult,
  ReviewScope,
  CatalogItem,
  ImportStatus,
  ChapterProgressItem,
  MarkReadResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((d: { msg: string }) => d.msg).join(", "));
    }
    throw new Error(typeof detail === "string" ? detail : `Request failed: ${res.status}`);
  }

  return res.json();
}

// --- Auth ---

export async function register(data: UserCreate): Promise<TokenResponse> {
  return request<TokenResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function login(data: UserLogin): Promise<TokenResponse> {
  return request<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function logout(): Promise<void> {
  await request<{ message: string }>("/api/auth/logout", {
    method: "POST",
  });
}

// --- Words ---

export async function addWord(
  data: WordCreateRequest,
): Promise<AddWordResponse> {
  return request<AddWordResponse>("/api/words", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function lookupWord(word: string): Promise<WordResponse[]> {
  return request<WordResponse[]>(
    `/api/words/lookup/${encodeURIComponent(word)}`,
  );
}

export async function searchWords(query: string): Promise<WordResponse[]> {
  return request<WordResponse[]>(
    `/api/words/search?q=${encodeURIComponent(query)}`,
  );
}

export async function exportVault(): Promise<WordResponse[]> {
  return request<WordResponse[]>("/api/words/export");
}

// --- Books ---

export async function getBooks(): Promise<BookListItem[]> {
  return request<BookListItem[]>("/api/books");
}

export async function getBookDetails(
  bookName: string,
): Promise<BookDetailResponse> {
  return request<BookDetailResponse>(
    `/api/books/${encodeURIComponent(bookName)}`,
  );
}

// --- Review ---

export async function getDueWords(
  scope?: ReviewScope,
): Promise<WordResponse[]> {
  const params = new URLSearchParams();
  if (scope?.book) params.set("book", scope.book);
  if (scope?.chapter) params.set("chapter", scope.chapter);
  const qs = params.toString();
  return request<WordResponse[]>(`/api/review/due${qs ? `?${qs}` : ""}`);
}

export async function submitAnswer(
  wordId: number,
  answer: string,
): Promise<ReviewAnswerResponse> {
  return request<ReviewAnswerResponse>("/api/review/answer", {
    method: "POST",
    body: JSON.stringify({ word_id: wordId, answer }),
  });
}

export async function completeReview(
  correctCount: number,
  totalCount: number,
): Promise<ReviewSessionSummary> {
  return request<ReviewSessionSummary>("/api/review/complete", {
    method: "POST",
    body: JSON.stringify({
      correct_count: correctCount,
      total_count: totalCount,
    }),
  });
}

// --- Stats ---

export async function getProfile(): Promise<ProfileResponse> {
  return request<ProfileResponse>("/api/stats/profile");
}

// --- Achievements ---

export async function getAchievements(): Promise<AchievementResponse[]> {
  return request<AchievementResponse[]>("/api/achievements");
}

// --- WOTD ---

export async function getWotd(): Promise<WotdResponse> {
  return request<WotdResponse>("/api/wotd");
}

// --- Dictionary ---

export async function lookupDictionary(
  word: string,
): Promise<DictionaryResult> {
  return request<DictionaryResult>(
    `/api/dictionary/lookup/${encodeURIComponent(word)}`,
  );
}

// --- Catalog / auto-import ---

export async function searchCatalog(q: string): Promise<CatalogItem[]> {
  return request<CatalogItem[]>(`/api/catalog/search?q=${encodeURIComponent(q)}`);
}

export async function importBook(gutenbergId: number): Promise<ImportStatus> {
  return request<ImportStatus>(`/api/catalog/import/${gutenbergId}`, {
    method: "POST",
  });
}

export async function getImportStatus(gutenbergId: number): Promise<ImportStatus> {
  return request<ImportStatus>(`/api/catalog/import/${gutenbergId}/status`);
}

export async function getBookChapters(
  bookName: string,
): Promise<ChapterProgressItem[]> {
  return request<ChapterProgressItem[]>(
    `/api/catalog/books/${encodeURIComponent(bookName)}/chapters`,
  );
}

export async function markChapterRead(
  chapterId: number,
): Promise<MarkReadResponse> {
  return request<MarkReadResponse>(
    `/api/catalog/chapters/${chapterId}/mark-read`,
    { method: "POST" },
  );
}
