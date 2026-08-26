/** The items a run produced, shown exactly as the reviewer will judge them. */

import type { GenerateOut } from "@/api/types";
import { Badge, Card, CardHeader } from "@/components/ui";

type Candidate = {
  qtype: string;
  stem: string;
  options: { key: string; text: string }[];
  answer_keys: string[];
  explanation?: string;
  difficulty: string;
  quality_score: number;
};

export function GeneratedItems({ result }: { result: GenerateOut }) {
  const questions = (result.questions ?? []) as unknown as Candidate[];
  const psych = (result.psych_items ?? []) as { test_type: string; prompt: string }[];
  const interview = (result.interview_questions ?? []) as { category: string; question: string }[];

  return (
    <div className="space-y-6">
      {questions.length > 0 && (
        <Card>
          <CardHeader title="Questions" subtitle={`${questions.length} accepted`} />
          <ul className="divide-y divide-ink-100">
            {questions.map((question, index) => (
              <li key={index} className="px-5 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <p className="min-w-0 text-ink-900">{question.stem}</p>
                  <div className="flex shrink-0 gap-2">
                    <Badge>{question.qtype.replace(/_/g, " ")}</Badge>
                    <Badge tone={question.quality_score >= 0.9 ? "green" : "amber"}>
                      {question.quality_score.toFixed(2)}
                    </Badge>
                  </div>
                </div>

                {question.options.length > 0 && (
                  <ul className="mt-3 grid gap-1.5 sm:grid-cols-2">
                    {question.options.map((option) => {
                      const correct = question.answer_keys.includes(option.key);
                      return (
                        <li
                          key={option.key}
                          className={`rounded-lg px-3 py-1.5 text-sm ring-1 ${
                            correct
                              ? "bg-success-50 text-ink-800 ring-success-500/40"
                              : "text-ink-600 ring-ink-200"
                          }`}
                        >
                          <span className="mr-2 font-mono uppercase text-ink-500">
                            {option.key}
                          </span>
                          {option.text}
                        </li>
                      );
                    })}
                  </ul>
                )}

                {question.options.length === 0 && question.answer_keys.length > 0 && (
                  <p className="mt-2 text-sm text-ink-600">
                    Answer: <span className="font-medium text-ink-800">{question.answer_keys.join(", ")}</span>
                  </p>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {psych.length > 0 && (
        <Card>
          <CardHeader title="Projective items" subtitle="SCT stems and SRT situations" />
          <ul className="divide-y divide-ink-100">
            {psych.map((item, index) => (
              <li key={index} className="flex items-start gap-3 px-5 py-3">
                <Badge>{item.test_type.toUpperCase()}</Badge>
                <p className="text-sm text-ink-800">{item.prompt}</p>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {interview.length > 0 && (
        <Card>
          <CardHeader title="Interview questions" />
          <ul className="divide-y divide-ink-100">
            {interview.map((item, index) => (
              <li key={index} className="flex items-start gap-3 px-5 py-3">
                <Badge>{item.category.replace(/_/g, " ")}</Badge>
                <p className="text-sm text-ink-800">{item.question}</p>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {questions.length === 0 && psych.length === 0 && interview.length === 0 && (
        <Card className="p-6">
          <p className="text-ink-700">
            Nothing survived the critic. The trace above shows where the candidates were
            lost — usually stems that need the previous sentence, or an answer that appears
            in the question.
          </p>
        </Card>
      )}
    </div>
  );
}
