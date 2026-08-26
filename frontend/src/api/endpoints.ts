/**
 * Typed wrappers over the endpoints this app actually calls.
 *
 * Grouped by the screen that uses them rather than by router, so adding a page
 * means adding one block here and nothing else in the HTTP layer.
 */

import { api, uploadForm } from "./client";
import type * as T from "./types";

export const auth = {
  register: (body: T.RegisterIn) =>
    api.post<T.AuthOut>("/auth/register", body, { anonymous: true }),

  login: (body: T.LoginIn) => api.post<T.AuthOut>("/auth/login", body, { anonymous: true }),

  me: () => api.get<T.UserPublic>("/auth/me"),

  /** Ready-made accounts, when the deployment allows them. Never on production. */
  demo: () =>
    api.get<{
      enabled: boolean;
      accounts: { label: string; description: string; email: string; password: string }[];
    }>("/auth/demo", undefined, undefined),

  logout: (refresh_token: string) => api.post<{ detail: string }>("/auth/logout", { refresh_token }),

  changePassword: (body: { current_password: string; new_password: string }) =>
    api.post<{ detail: string }>("/auth/change-password", body),
};

export const me = {
  dashboard: () => api.get<T.Dashboard>("/me/dashboard"),
  stats: () => api.get<T.UserStats>("/me/stats"),
  update: (body: T.ProfileUpdate) => api.patch<T.UserPublic>("/me", body),
  attempts: (page = 1, size = 20) =>
    api.get<T.Page<T.AttemptSummary>>("/attempts", { page, size }),
};

export const catalog = {
  services: () => api.get<T.Service[]>("/catalog/services"),
  service: (code: T.ServiceCode) => api.get<T.ServiceOverview>(`/catalog/services/${code}`),
  stages: () => api.get<T.Stage[]>("/catalog/stages"),
  programs: (service_id?: number) => api.get<T.Program[]>("/catalog/programs", { service_id }),
  program: (slug: string) => api.get<T.Program>(`/catalog/programs/${slug}`),
  modules: (query: { service_id?: number; stage_id?: number } = {}) =>
    api.get<T.Module[]>("/catalog/modules", query),
  module: (ref: string | number) => api.get<T.ModuleDetail>(`/catalog/modules/${ref}`),
};

export const practice = {
  questions: (query: { module_id?: number; topic_id?: number; page?: number; size?: number }) =>
    api.get<T.Page<T.Question>>("/questions", query),

  tests: (query: { service_id?: number; is_mock?: boolean } = {}) =>
    api.get<T.TestTemplate[]>("/tests", query),

  start: (body: T.AttemptStart) => api.post<T.Attempt>("/attempts", body),

  resume: (id: number) => api.get<T.Attempt>(`/attempts/${id}`),

  submit: (id: number, body: T.AttemptSubmit) =>
    api.post<T.AttemptResult>(`/attempts/${id}/submit`, body),

  result: (id: number) => api.get<T.AttemptResult>(`/attempts/${id}/result`),

  abandon: (id: number) => api.post<{ detail: string }>(`/attempts/${id}/abandon`),

  report: (questionId: number, body: { reason: string; note?: string }) =>
    api.post<unknown>(`/questions/${questionId}/report`, body),
};

export const issb = {
  startPsych: (body: { test_type: T.PsychTestType; count?: number }) =>
    api.post<T.PsychSession>("/issb/psych/sessions", body),

  submitPsych: (
    id: number,
    body: { responses: { item_id: number; text: string; ms: number; skipped?: boolean }[]; duration_sec: number },
  ) => api.post<T.PsychResult>(`/issb/psych/sessions/${id}/submit`, body),

  psychResult: (id: number) => api.get<T.PsychResult>(`/issb/psych/sessions/${id}`),

  psychHistory: (page = 1, size = 20, test_type?: T.PsychTestType) =>
    api.get<T.Page<T.PsychSessionSummary>>("/issb/psych/sessions", { page, size, test_type }),

  gtoTasks: (
    query: { task_type?: string; venue?: T.GtoVenue; service?: T.ServiceCode; size?: number } = {},
  ) => api.get<T.Page<T.GtoTask>>("/issb/gto/tasks", { size: 50, ...query }),

  gtoTask: (id: number) => api.get<T.GtoTask>(`/issb/gto/tasks/${id}`),

  submitGto: (taskId: number, body: { body: string; duration_sec: number }) =>
    api.post<T.GtoResult>(`/issb/gto/tasks/${taskId}/submit`, body),

  startInterview: (body: { count?: number; service?: T.ServiceCode }) =>
    api.post<T.InterviewSession>("/issb/interview/sessions", body),

  submitInterview: (
    id: number,
    body: { exchanges: { question_id: number; answer: string; ms: number }[]; duration_sec: number },
  ) => api.post<T.InterviewResult>(`/issb/interview/sessions/${id}/submit`, body),

  interviewResult: (id: number) => api.get<T.InterviewResult>(`/issb/interview/sessions/${id}`),

  olqProfile: () => api.get<T.OlqProfile>("/issb/olq-profile"),
};

export const content = {
  /**
   * Current affairs, read live from news feeds and never stored.
   * `stored: false` in the response is the API stating that plainly.
   */
  news: (days = 7, limit = 12) =>
    api.get<{
      stored: boolean;
      items: {
        title: string;
        summary: string;
        source: string;
        url: string;
        published: string | null;
      }[];
    }>("/news", { days, limit }),

  articles: (query: { page?: number; size?: number; category?: string } = {}) =>
    api.get<T.Page<T.ArticleSummary>>("/articles", query),
  article: (ref: string) => api.get<T.Article>(`/articles/${ref}`),
  notes: (query: { module_id?: number; page?: number } = {}) =>
    api.get<T.Page<T.Note>>("/notes", query),
  announcements: () => api.get<T.Announcement[]>("/announcements"),
  testimonials: () => api.get<T.Testimonial[]>("/testimonials"),
  contact: (body: { name: string; email: string; message: string; subject?: string; phone?: string }) =>
    api.post<{ detail: string }>("/contact", body),
};

/**
 * Staff endpoints. Everything here is gated server-side as well -- the UI hides
 * these screens from students, but the API is what actually enforces it.
 */
export const admin = {
  questions: (query: {
    page?: number;
    size?: number;
    module_id?: number;
    status?: T.ContentStatus;
    difficulty?: T.Difficulty;
    qtype?: T.QuestionType;
    origin?: T.Origin;
    q?: string;
  }) => api.get<T.Page<T.QuestionAdmin>>("/admin/questions", query),

  queue: (page = 1, size = 20) =>
    api.get<T.Page<T.QuestionAdmin>>("/admin/questions/queue", { page, size }),

  createQuestion: (body: T.QuestionIn) => api.post<T.QuestionAdmin>("/admin/questions", body),

  updateQuestion: (id: number, body: T.QuestionUpdate) =>
    api.patch<T.QuestionAdmin>(`/admin/questions/${id}`, body),

  deleteQuestion: (id: number) => api.delete<{ detail: string }>(`/admin/questions/${id}`),

  review: (id: number, body: { status: T.ContentStatus; note?: string }) =>
    api.post<{ detail: string }>(`/admin/questions/${id}/review`, body),

  bulkReview: (body: T.BulkReviewIn) => api.post<{ detail: string }>("/admin/questions/review", body),

  articles: (query: { page?: number; size?: number; q?: string } = {}) =>
    api.get<T.Page<T.Article>>("/admin/articles", query),

  article: (id: number) => api.get<T.Article>(`/admin/articles/${id}`),

  createArticle: (body: T.ArticleIn) => api.post<T.Article>("/admin/articles", body),

  updateArticle: (id: number, body: T.ArticleUpdate) =>
    api.patch<T.Article>(`/admin/articles/${id}`, body),

  deleteArticle: (id: number) => api.delete<{ detail: string }>(`/admin/articles/${id}`),

  announce: (body: T.AnnouncementIn) => api.post<T.Announcement>("/admin/announcements", body),

  users: (query: { page?: number; size?: number; q?: string; role?: T.Role } = {}) =>
    api.get<T.Page<T.AdminUser>>("/admin/users", query),

  updateUser: (id: number, body: T.AdminUserUpdate) =>
    api.patch<T.AdminUser>(`/admin/users/${id}`, body),

  contactMessages: (query: { page?: number; handled?: boolean } = {}) =>
    api.get<T.Page<T.ContactMessage>>("/admin/contact-messages", query),

  size: () => api.get<Record<string, number>>("/admin/maintenance/size"),
  prune: () => api.post<Record<string, number>>("/admin/maintenance/prune"),
  recount: () => api.post<{ detail: string }>("/admin/maintenance/recount"),
};

/** The local question engine. No external AI service is involved. */
export const agent = {
  status: () =>
    api.get<{
      engine: string;
      note: string | null;
      uses_external_api: boolean;
      min_quality: number;
      max_questions_per_run: number;
      min_article_chars: number;
      retained_runs: number;
    }>("/agent/status"),

  generate: (articleId: number, body: T.GenerateIn) =>
    api.post<T.GenerateOut>(`/agent/articles/${articleId}/generate`, body),

  preview: (body: T.PreviewIn) => api.post<T.GenerateOut>("/agent/preview", body),

  runs: (query: { page?: number; size?: number; article_id?: number } = {}) =>
    api.get<T.Page<T.AgentRun>>("/agent/runs", query),

  run: (id: number) => api.get<T.AgentRun>(`/agent/runs/${id}`),
};

export const fitness = {
  log: (body: T.PhysicalLogIn) => api.post<T.PhysicalLog>("/me/physical", body),
  history: (page = 1, size = 30) => api.get<T.Page<T.PhysicalLog>>("/me/physical", { page, size }),
  progress: (programId?: number) =>
    api.get<T.PhysicalProgress>("/me/physical/progress", { program_id: programId }),
};

/**
 * Practising on paper, then photographing the sheet.
 *
 * The transcribe step returns a *draft* the candidate corrects; nothing is
 * analysed until they confirm it, because handwriting recognition is not
 * reliable enough to be trusted silently. The image is never stored.
 */
export const sheets = {
  plan: (test_type: T.PsychTestType, count?: number) =>
    api.get<T.SheetPlan>("/issb/psych/sheet", { test_type, count }),

  transcribe: async (file: File, itemCount: number) => {
    const body = new FormData();
    body.append("file", file);
    body.append("item_count", String(itemCount));
    // Multipart, so this bypasses the JSON helper but keeps the auth + refresh
    // behaviour by going through the same request layer.
    return uploadForm<T.Transcription>("/issb/psych/transcribe", body);
  },

  submit: (body: T.SheetSubmit) => api.post<T.PsychResult>("/issb/psych/sheet", body),
};

export const ppdt = {
  pictures: () => api.get<T.PsychItem[]>("/issb/ppdt/pictures"),
  submit: (body: T.PpdtSubmit) => api.post<T.PpdtResult>("/issb/ppdt/submit", body),
};

export const progress = {
  olqTrend: (limit = 20) => api.get<T.TrendPoint[]>("/issb/olq-trend", { limit }),
};
