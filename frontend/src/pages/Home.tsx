import { Link } from "react-router-dom";

import { content } from "@/api/endpoints";
import { Brain, Chart, ChevronRight, Target, Users } from "@/components/icons";
import { Badge, Button, Card } from "@/components/ui";
import { useAuth } from "@/auth/useAuth";
import { ServiceAvatar } from "@/components/ServiceAvatar";
import { formatDate } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";

const FEATURES = [
  {
    icon: Target,
    title: "The whole funnel",
    body: "Registration through initial test, physical, medical, ISSB and the merit list, for the Army, PAF and Navy, each with its own entry schemes and standards.",
  },
  {
    icon: Brain,
    title: "Full ISSB simulation",
    body: "PPDT, a timed WAT, SCT, SRT or TAT, GTO planning tasks and a mock interview, then see which Officer Like Qualities your writing actually projects.",
  },
  {
    icon: Chart,
    title: "Practice that adapts",
    body: "Questions you get wrong come back on a spaced-repetition schedule, and your weakest topics surface on the dashboard.",
  },
  {
    icon: Users,
    title: "Practise on paper",
    body: "Print a sheet, solve it by hand under a clock, photograph it, and get the same read-out as a typed sitting.",
  },
];

const SERVICES = [
  { code: "army", name: "Pakistan Army", note: "PMA Long Course, TCC, LCC" },
  { code: "air_force", name: "Pakistan Air Force", note: "GD Pilot, Aeronautical Engineering" },
  { code: "navy", name: "Pakistan Navy", note: "PN Cadet, Short Service" },
];

export function Home() {
  const { isAuthenticated } = useAuth();
  // Live from the feeds, not from the database -- see /news.
  const { data: news } = useAsync(() => content.news(7, 4), []);

  return (
    <div>
      <section className="relative overflow-hidden bg-army-500 text-white">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-16 lg:grid-cols-[1.15fr_1fr] lg:items-center lg:py-20">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-white/70">
              Army · Air Force · Navy
            </p>
            <h1 className="mt-3 max-w-2xl font-display text-4xl font-bold leading-tight sm:text-5xl">
              Prepare for selection the way the board actually assesses you.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-white/90">
              Written test practice on your service&apos;s real pattern, physical standards, and a
              complete ISSB simulation, from screening day through the conference.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={isAuthenticated ? "/dashboard" : "/register"}>
                <Button size="lg" variant="inverse">
                  {isAuthenticated ? "Go to dashboard" : "Start free"}
                </Button>
              </Link>
              <Link to="/services">
                <Button size="lg" variant="outline">
                  Explore the services
                  <ChevronRight size={18} />
                </Button>
              </Link>
            </div>
          </div>

          {/* Drawn, not photographed: three avatars weigh a few hundred bytes
              between them where the officer photographs were 2.2 MB -- bandwidth
              a free tier pays for on every cold visit.

              Framed in circles so the figure ends on a deliberate edge. Sitting
              them loose on the panel let the section boundary cut the shoulders
              flat, which reads as a clipped image rather than a design. */}
          <div className="hidden items-center justify-center gap-4 lg:flex">
            {SERVICES.map((service, index) => (
              <span
                key={service.code}
                className={`grid place-items-center overflow-hidden rounded-full bg-white/10 ring-2 ring-white/25 ${
                  index === 1 ? "h-48 w-48" : "h-36 w-36"
                }`}
              >
                <ServiceAvatar service={service.code} size={index === 1 ? 176 : 132} />
              </span>
            ))}
          </div>
        </div>
      </section>

      <section aria-labelledby="services-heading" className="mx-auto max-w-6xl px-4 py-16">
        <h2 id="services-heading" className="font-display text-2xl font-bold text-ink-900">
          Three services, three different tests
        </h2>
        <p className="mt-2 max-w-2xl text-ink-500">
          They are not interchangeable. The Army tests General Knowledge and Islamiat, the PAF
          tests Physics and no General Knowledge at all, and the Navy weights intelligence three
          to one towards non-verbal.
        </p>

        <div className="mt-8 grid gap-5 sm:grid-cols-3">
          {SERVICES.map((service) => (
            <Link key={service.code} to={`/services/${service.code}`} className="group">
              <Card className="flex h-full flex-col overflow-hidden transition hover:ring-2 hover:ring-army-500">
                {/* Bottom-aligned so all three officers stand on one line: the
                    cut-outs range from 0.64 to 1.06 in aspect ratio, and
                    centring them left each at a different height. */}
                <div className="flex h-40 items-end justify-center bg-ink-100">
                  <ServiceAvatar
                    service={service.code}
                    size={152}
                    className="transition duration-300 group-hover:scale-105"
                  />
                </div>
                <div className="p-5">
                  <h3 className="font-semibold text-ink-900">{service.name}</h3>
                  <p className="mt-1 text-sm text-ink-500">{service.note}</p>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section className="border-y border-ink-200/70 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <div className="grid gap-5 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <Card key={feature.title} className="p-6">
                <feature.icon size={24} className="text-army-500" />
                <h2 className="mt-3 font-display text-lg font-bold text-ink-900">
                  {feature.title}
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-ink-500">{feature.body}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {news && news.items.length > 0 && (
        <section aria-labelledby="news-heading" className="mx-auto max-w-6xl px-4 py-16">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 id="news-heading" className="font-display text-2xl font-bold text-ink-900">
                This week in current affairs
              </h2>
              <p className="mt-2 max-w-2xl text-ink-500">
                Read live from Pakistani news feeds. The stories are not stored, only the
                questions written from them, which is what stays useful once the news is old.
              </p>
            </div>
            <Link to="/articles" className="text-sm font-medium text-army-600 hover:underline">
              All current affairs
            </Link>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            {news.items.map((story) => (
              <a
                key={story.url || story.title}
                href={story.url}
                target="_blank"
                rel="noreferrer noopener"
              >
                <Card className="h-full p-5 transition hover:ring-2 hover:ring-army-500">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge>{story.source}</Badge>
                    {story.published && (
                      <span className="text-xs text-ink-500">{formatDate(story.published)}</span>
                    )}
                  </div>
                  <h3 className="mt-2 font-semibold leading-snug text-ink-900">{story.title}</h3>
                  {story.summary && (
                    <p className="mt-2 line-clamp-3 text-sm text-ink-500">{story.summary}</p>
                  )}
                </Card>
              </a>
            ))}
          </div>
        </section>
      )}

      <section className="border-t border-ink-200/70 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-16 text-center">
          <h2 className="font-display text-2xl font-bold text-ink-900">
            Recommendation starts with preparation
          </h2>
          <p className="mt-3 text-ink-500">
            Create a free account and start with a twenty-question drill in the module of your
            choice, or sign in with the demo account and look around first.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link to={isAuthenticated ? "/practice" : "/register"}>
              <Button size="lg">
                {isAuthenticated ? "Start practising" : "Create an account"}
              </Button>
            </Link>
            {!isAuthenticated && (
              <Link to="/login">
                <Button size="lg" variant="secondary">
                  Try the demo
                </Button>
              </Link>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
