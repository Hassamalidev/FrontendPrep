import { useState } from "react";

import { ApiError } from "@/api/client";
import { admin } from "@/api/endpoints";
import type { Role } from "@/api/types";
import { Alert, Badge, Button, Card, ErrorState, Field, Loading } from "@/components/ui";
import { useAuth } from "@/auth/useAuth";
import { useAsync } from "@/lib/useAsync";
import { formatDate } from "@/lib/format";

const ROLES: Role[] = ["student", "instructor", "admin", "super_admin"];

export function AdminUsers() {
  const { user: me } = useAuth();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const { data, error, loading, refetch } = useAsync(
    () => admin.users({ page, size: 20, q: query || undefined }),
    [page, query],
  );

  // Role and status changes are super-admin only, and the API also refuses a
  // self-edit -- so the controls are hidden for your own row rather than
  // offering an action that will fail.
  const isSuperAdmin = me?.role === "super_admin";

  async function change(id: number, body: { role?: Role; status?: "active" | "suspended" }) {
    setActionError(null);
    try {
      await admin.updateUser(id, body);
      refetch();
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not update the account.");
    }
  }

  if (loading) return <Loading label="Loading users" />;
  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Users</h1>
      <p className="mt-2 text-ink-500">
        {data?.total ?? 0} account{data?.total === 1 ? "" : "s"}.
        {isSuperAdmin ? "" : " Only a super admin can change roles."}
      </p>

      <Card className="mt-6 p-4">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            setQuery(search.trim());
          }}
        >
          <Field
            className="min-w-64 flex-1"
            label="Search"
            name="q"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Name or email"
          />
          <Button type="submit">Search</Button>
        </form>
      </Card>

      {actionError && (
        <div className="mt-4">
          <Alert tone="error">{actionError}</Alert>
        </div>
      )}

      <ul className="mt-6 space-y-3">
        {(data?.items ?? []).map((account) => (
          <li key={account.id}>
            <Card className="flex flex-wrap items-center justify-between gap-4 p-4">
              <div className="min-w-0">
                <p className="font-medium text-ink-900">{account.full_name}</p>
                <p className="text-sm text-ink-500">{account.email}</p>
                <p className="mt-1 text-xs text-ink-500">
                  Joined {formatDate(account.created_at)}
                  {account.last_login_at ? ` - last seen ${formatDate(account.last_login_at)}` : ""}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={account.status === "active" ? "green" : "red"}>{account.status}</Badge>

                {isSuperAdmin && account.id !== me?.id ? (
                  <>
                    <label className="sr-only" htmlFor={`role-${account.id}`}>
                      Role for {account.full_name}
                    </label>
                    <select
                      id={`role-${account.id}`}
                      value={account.role}
                      onChange={(event) =>
                        void change(account.id, { role: event.target.value as Role })
                      }
                      className="rounded-lg border border-ink-200 bg-white px-2 py-1 text-sm"
                    >
                      {ROLES.map((role) => (
                        <option key={role} value={role}>
                          {role.replace(/_/g, " ")}
                        </option>
                      ))}
                    </select>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        void change(account.id, {
                          status: account.status === "active" ? "suspended" : "active",
                        })
                      }
                    >
                      {account.status === "active" ? "Suspend" : "Restore"}
                    </Button>
                  </>
                ) : (
                  <Badge>{account.role.replace(/_/g, " ")}</Badge>
                )}
              </div>
            </Card>
          </li>
        ))}
      </ul>

      {(data?.pages ?? 1) > 1 && (
        <div className="mt-8 flex items-center justify-between">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <p className="text-sm text-ink-500">
            Page {data?.page} of {data?.pages}
          </p>
          <Button
            variant="secondary"
            disabled={page >= (data?.pages ?? 1)}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
