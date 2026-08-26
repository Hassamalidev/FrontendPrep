/**
 * Domain type aliases.
 *
 * `schema.d.ts` is generated from the backend's own OpenAPI document
 * (`npm run gen:api`), so these names are the single source of truth for every
 * payload shape in the app. Renaming a field in a Pydantic model breaks the
 * build here rather than at runtime in a user's browser.
 *
 * Only aliases belong in this file -- no hand-written shapes, or the guarantee
 * above stops holding.
 */

import type { components } from "./schema";

type Schemas = components["schemas"];

// --- Auth and identity -----------------------------------------------------
export type UserPublic = Schemas["UserPublic"];
export type TokenPair = Schemas["TokenPair"];
export type AuthOut = Schemas["AuthOut"];
export type RegisterIn = Schemas["RegisterIn"];
export type LoginIn = Schemas["LoginIn"];
export type ProfileUpdate = Schemas["ProfileUpdate"];
export type UserStats = Schemas["UserStatsOut"];
export type Dashboard = Schemas["DashboardOut"];

// --- Catalog ---------------------------------------------------------------
export type Service = Schemas["ServiceOut"];
export type ServiceOverview = Schemas["ServiceOverviewOut"];
export type Program = Schemas["ProgramOut"];
export type Stage = Schemas["StageOut"];
export type Module = Schemas["ModuleOut"];
export type ModuleDetail = Schemas["ModuleDetailOut"];
export type Topic = Schemas["TopicOut"];

// --- Practice --------------------------------------------------------------
export type Question = Schemas["QuestionOut"];
export type QuestionReview = Schemas["QuestionReviewOut"];
export type TestTemplate = Schemas["TestTemplateOut"];
export type Attempt = Schemas["AttemptOut"];
export type AttemptStart = Schemas["AttemptStartIn"];
export type AttemptSubmit = Schemas["AttemptSubmitIn"];
export type AttemptResult = Schemas["AttemptResultOut"];
export type AttemptSummary = Schemas["AttemptSummaryOut"];
export type AnswerIn = Schemas["AnswerIn"];

// --- ISSB simulation -------------------------------------------------------
export type PsychItem = Schemas["PsychItemOut"];
export type PsychSession = Schemas["PsychSessionOut"];
export type PsychResult = Schemas["PsychResultOut"];
export type PsychSessionSummary = Schemas["PsychSessionSummaryOut"];
export type GtoTask = Schemas["GtoTaskOut"];
export type GtoVenue = Schemas["GtoVenue"];
export type GtoResult = Schemas["GtoResultOut"];
export type InterviewSession = Schemas["InterviewSessionOut"];
export type InterviewResult = Schemas["InterviewResultOut"];
export type OlqProfile = Schemas["OlqProfileOut"];
export type Analysis = Schemas["AnalysisOut"];

// --- Answer sheets and PPDT ------------------------------------------------
export type Transcription = Schemas["TranscriptionOut"];
export type SheetSubmit = Schemas["SheetSubmitIn"];
export type SheetPlan = Schemas["SheetPlanOut"];
export type PpdtSubmit = Schemas["PpdtSubmitIn"];
export type PpdtResult = Schemas["PpdtResultOut"];
export type PpdtPerception = Schemas["PpdtPerception"];

/** One point on the progress chart. The API returns these untyped. */
export type TrendPoint = {
  id: number;
  test_type: string;
  submitted_at: string;
  overall_score: number;
  answered: number;
  items: number;
  source: string;
};

// --- Content ---------------------------------------------------------------
export type ArticleSummary = Schemas["ArticleSummaryOut"];
export type Article = Schemas["ArticleOut"];
export type Note = Schemas["NoteOut"];
export type Announcement = Schemas["AnnouncementOut"];
export type Testimonial = Schemas["TestimonialOut"];

// --- Staff -----------------------------------------------------------------
export type QuestionAdmin = Schemas["QuestionAdminOut"];
export type QuestionIn = Schemas["QuestionIn"];
export type QuestionUpdate = Schemas["QuestionUpdate"];
export type BulkReviewIn = Schemas["BulkReviewIn"];
export type AdminUser = Schemas["AdminUserOut"];
export type AdminUserUpdate = Schemas["AdminUserUpdate"];
export type ContactMessage = Schemas["ContactMessageOut"];
export type ArticleIn = Schemas["ArticleIn"];
export type ArticleUpdate = Schemas["ArticleUpdate"];
export type AnnouncementIn = Schemas["AnnouncementIn"];
export type ContentStatus = Schemas["ContentStatus"];
export type QuestionType = Schemas["QuestionType"];
export type Origin = Schemas["Origin"];

// --- Generation ------------------------------------------------------------
export type GenerateIn = Schemas["GenerateIn"];
export type PreviewIn = Schemas["PreviewIn"];
export type GenerateOut = Schemas["GenerateOut"];
export type AgentRun = Schemas["AgentRunOut"];

// --- Fitness ---------------------------------------------------------------
export type PhysicalLog = Schemas["PhysicalLogOut"];
export type PhysicalLogIn = Schemas["PhysicalLogIn"];
export type PhysicalProgress = Schemas["PhysicalProgressOut"];

// --- Enumerations ----------------------------------------------------------
export type ServiceCode = Schemas["ServiceCode"];
export type Difficulty = Schemas["Difficulty"];
export type PsychTestType = Schemas["PsychTestType"];
export type Role = Schemas["Role"];

/** The paginated envelope, which OpenAPI generates once per item type. */
export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
};
