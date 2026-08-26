/**
 * Where a module is actually practised.
 *
 * Most modules hold a bank of written questions and are drilled in place. Five
 * do not: the ISSB-stage modules and physical preparation exist so the syllabus
 * reads as one continuous funnel, but their practice lives in the simulation
 * suite and the training log.
 *
 * Without this mapping those five look like empty modules -- the catalog showed
 * them as "0 questions" and the practice page filed them under "Coming soon",
 * which told a student the flagship feature was unbuilt while it sat one click
 * away.
 */

export type ModuleDestination = {
  to: string;
  /** What the student does there, for the card. */
  action: string;
  /** Why it is not a question drill. */
  note: string;
};

const ELSEWHERE: Record<string, ModuleDestination> = {
  "issb-screening": {
    to: "/issb",
    action: "Open the ISSB suite",
    note: "Screening-day practice runs in the simulation suite.",
  },
  "psychological-tests": {
    to: "/issb",
    action: "Sit a psychological test",
    note: "WAT, SCT, SRT and TAT run under their own clock in the ISSB suite.",
  },
  "gto-series": {
    to: "/issb/gto",
    action: "Plan a GTO task",
    note: "GTO tasks are briefs you plan, not questions you answer.",
  },
  "interview-preparation": {
    to: "/issb/interview",
    action: "Run a mock interview",
    note: "The interview is practised as a full mock in the ISSB suite.",
  },
  "physical-preparation": {
    to: "/profile",
    action: "Log your training",
    note: "Physical standards are tracked against your entry scheme in your profile.",
  },
};

/** Null when the module is an ordinary question bank. */
export function practisedElsewhere(slug: string): ModuleDestination | null {
  return ELSEWHERE[slug] ?? null;
}
