import { useState, type FormEvent } from "react";

import { ApiError } from "@/api/client";
import { content } from "@/api/endpoints";
import { Alert, Button, Card, Field, TextArea } from "@/components/ui";

export function Contact() {
  const [form, setForm] = useState({ name: "", email: "", phone: "", subject: "", message: "" });
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    setFieldErrors({});
    try {
      await content.contact({
        name: form.name,
        email: form.email,
        message: form.message,
        subject: form.subject || undefined,
        phone: form.phone || undefined,
      });
      setSent(true);
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFieldErrors(caught.fieldErrors);
      } else {
        setError("Could not send your message. Check your connection and try again.");
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="font-display text-3xl font-bold text-ink-900">Contact</h1>
      <p className="mt-2 text-ink-500">
        Questions about preparation, a problem with the site, or a correction to a question.
      </p>

      <Card className="mt-8 p-6">
        {sent ? (
          <Alert tone="success">
            Thank you. Your message has been received and we will get back to you shortly.
          </Alert>
        ) : (
          <form onSubmit={submit} noValidate className="space-y-4">
            {error && <Alert tone="error">{error}</Alert>}

            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Your name"
                name="name"
                required
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                error={fieldErrors.name}
              />
              <Field
                label="Email"
                name="email"
                type="email"
                required
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                error={fieldErrors.email}
              />
              <Field
                label="Phone"
                name="phone"
                value={form.phone}
                onChange={(event) => setForm({ ...form, phone: event.target.value })}
              />
              <Field
                label="Subject"
                name="subject"
                value={form.subject}
                onChange={(event) => setForm({ ...form, subject: event.target.value })}
              />
            </div>

            <TextArea
              label="Message"
              name="message"
              rows={6}
              required
              value={form.message}
              onChange={(event) => setForm({ ...form, message: event.target.value })}
              error={fieldErrors.message}
            />

            <Button type="submit" size="lg" loading={sending}>
              Send message
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
