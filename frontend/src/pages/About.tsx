import { Link } from "react-router-dom";

import { Button, Card } from "@/components/ui";

export function About() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="font-display text-3xl font-bold text-ink-900">About Frontline Prep</h1>

      <div className="mt-6 space-y-5 leading-relaxed text-ink-700">
        <p>
          This platform prepares candidates for commissioned entry into the Pakistan Army,
          Air Force and Navy — the whole funnel, from registration and the initial written
          test through the physical and medical standards to the five days at an ISSB centre.
        </p>
        <p>
          Most preparation material stops at the written test. The part candidates find
          hardest is the part that cannot be revised from a book: the psychological battery,
          the group tasks, and the interview. Those are simulated here as closely as a single
          candidate at a screen allows.
        </p>
      </div>

      <Card className="mt-8 p-6">
        <h2 className="font-display text-lg font-bold text-ink-900">What the analysis is</h2>
        <p className="mt-2 text-ink-700">
          The projective tests have no answer key, so nothing here grades you. What the
          platform does instead is measure observable properties of your writing — how much
          you attempted, how quickly, how decisively, whether you described concrete actions,
          whether other people appear in your responses — and report which Officer Like
          Qualities those choices project.
        </p>
        <p className="mt-3 text-ink-700">
          It is a coaching signal, not an assessment of character, and a real board scores
          you on far more than words on a page. The difference between{" "}
          <em>“I would think about the problem”</em> and{" "}
          <em>“I informed the JCO, split the party in two and cleared the route by 0900”</em>{" "}
          is most of what WAT and SRT coaching is, and that difference is measurable.
        </p>
      </Card>

      <Card className="mt-6 p-6">
        <h2 className="font-display text-lg font-bold text-ink-900">
          How the questions are written
        </h2>
        <p className="mt-2 text-ink-700">
          Current-affairs questions are generated from published articles by a pipeline that
          runs entirely on this platform's own servers — no external AI service is called and
          no data leaves the system. Every generated question is reviewed by a person before
          any candidate sees it.
        </p>
      </Card>

      <div className="mt-10 flex flex-wrap gap-3">
        <Link to="/services">
          <Button>Explore the services</Button>
        </Link>
        <Link to="/contact">
          <Button variant="secondary">Contact us</Button>
        </Link>
      </div>
    </div>
  );
}
