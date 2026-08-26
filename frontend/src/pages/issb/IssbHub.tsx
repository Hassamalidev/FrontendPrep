import { Link } from "react-router-dom";

import { issb } from "@/api/endpoints";
import { OlqBars } from "@/components/charts/OlqBars";
import { Book, Brain, Chart, ChevronRight, Users } from "@/components/icons";
import { Button, Card, CardHeader } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

const TESTS = [
  {
    to: "/issb/ppdt",
    name: "Picture Perception & Description",
    short: "PPDT",
    detail:
      "Screening day. Thirty seconds to perceive, a proforma, then a four-minute story that has to match it.",
  },
  {
    to: "/issb/psych/wat",
    name: "Word Association Test",
    short: "WAT",
    detail: "60 words, 15 seconds each. Write the first sentence that comes to mind.",
  },
  {
    to: "/issb/psych/sct",
    name: "Sentence Completion Test",
    short: "SCT",
    detail: "60 incomplete sentences, 30 seconds each.",
  },
  {
    to: "/issb/psych/srt",
    name: "Situation Reaction Test",
    short: "SRT",
    detail: "60 situations, 30 seconds each. Say what you would do.",
  },
  {
    to: "/issb/psych/tat",
    name: "Thematic Apperception Test",
    short: "TAT",
    detail: "Hazy pictures. Write a story with a hero, an action and an outcome.",
  },
];

export function IssbHub() {
  const { data: profile } = useAsync(() => issb.olqProfile(), []);
  const hasProfile = (profile?.sessions_counted ?? 0) > 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-12">
      <h1 className="font-display text-3xl font-bold text-ink-900">ISSB simulation</h1>
      <p className="mt-2 max-w-2xl text-ink-500">
        The five days at a selection board, as far as they can be practised alone:
        the psychological battery under its real clock, the GTO planning tasks, and
        the interview.
      </p>

      <section aria-labelledby="psych-heading" className="mt-10">
        <div className="flex items-center gap-2">
          <Brain size={20} className="text-army-500" />
          <h2 id="psych-heading" className="font-display text-xl font-bold text-ink-900">
            Psychological tests
          </h2>
        </div>
        <p className="mt-1 text-sm text-ink-500">
          Timed, and the slide advances whether or not you have finished — as it does
          on the day.
        </p>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {TESTS.map((test) => (
            <Link key={test.to} to={test.to}>
              <Card className="h-full p-5 transition hover:ring-2 hover:ring-army-500">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-semibold text-ink-900">{test.name}</h3>
                    <p className="mt-1 text-sm text-ink-500">{test.detail}</p>
                  </div>
                  <span className="shrink-0 rounded-md bg-army-50 px-2 py-1 text-xs font-bold text-army-600">
                    {test.short}
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section aria-labelledby="paper-heading" className="mt-10">
        <div className="flex items-center gap-2">
          <Book size={20} className="text-army-500" />
          <h2 id="paper-heading" className="font-display text-xl font-bold text-ink-900">
            On paper
          </h2>
        </div>
        <p className="mt-1 text-sm text-ink-500">
          You will sit the real thing by hand, at speed, on numbered paper. Print a sheet,
          solve it under a clock, then photograph it for the same read-out.
        </p>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Link to="/issb/sheet">
            <Card className="h-full p-5 transition hover:ring-2 hover:ring-army-500">
              <h3 className="font-semibold text-ink-900">Print a practice sheet</h3>
              <p className="mt-1 text-sm text-ink-500">
                WAT, SCT or SRT, numbered and ruled, with the instructions as they are read out.
              </p>
            </Card>
          </Link>
          <Link to="/issb/upload">
            <Card className="h-full p-5 transition hover:ring-2 hover:ring-army-500">
              <h3 className="font-semibold text-ink-900">Upload a solved sheet</h3>
              <p className="mt-1 text-sm text-ink-500">
                Photograph it. The handwriting is read into a draft you correct, then analysed
                exactly as a typed sitting. The photo is never stored.
              </p>
            </Card>
          </Link>
        </div>
      </section>

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="gto-heading">
          <div className="flex items-center gap-2">
            <Users size={20} className="text-army-500" />
            <h2 id="gto-heading" className="font-display text-xl font-bold text-ink-900">
              GTO tasks
            </h2>
          </div>
          <Card className="mt-4 p-5">
            <p className="text-sm text-ink-600">
              Two halves over days three and four: three indoor tasks that are verbal and
              written, and six outdoor ones that are physical. Write the plan you would
              present and it is compared against a worked solution and the assessor rubric.
            </p>
            <Link to="/issb/gto" className="mt-4 inline-block">
              <Button>
                Open GTO tasks <ChevronRight size={16} />
              </Button>
            </Link>
          </Card>
        </section>

        <section aria-labelledby="interview-heading">
          <div className="flex items-center gap-2">
            <Chart size={20} className="text-army-500" />
            <h2 id="interview-heading" className="font-display text-xl font-bold text-ink-900">
              Mock interview
            </h2>
          </div>
          <Card className="mt-4 p-5">
            <p className="text-sm text-ink-600">
              Questions in the order an Interviewing Officer works through them —
              outward from you to your family, studies and the wider world.
            </p>
            <Link to="/issb/interview" className="mt-4 inline-block">
              <Button>
                Start an interview <ChevronRight size={16} />
              </Button>
            </Link>
          </Card>
        </section>
      </div>

      {hasProfile && profile && (
        <section aria-labelledby="profile-heading" className="mt-12">
          <h2 id="profile-heading" className="font-display text-xl font-bold text-ink-900">
            Your cumulative profile
          </h2>
          <Card className="mt-4">
            <CardHeader
              title="Officer Like Qualities"
              subtitle={`Averaged across ${profile.sessions_counted} sitting${
                profile.sessions_counted === 1 ? "" : "s"
              }`}
              action={
                <Link to="/issb/profile" className="text-sm font-medium text-army-600 hover:underline">
                  Details
                </Link>
              }
            />
            <div className="p-5">
              <OlqBars
                scores={profile.scores.slice(0, 6)}
                caption="Your six strongest signals so far."
              />
            </div>
          </Card>
        </section>
      )}
    </div>
  );
}
