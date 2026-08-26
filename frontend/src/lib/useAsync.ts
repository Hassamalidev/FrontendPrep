/**
 * Minimal data-fetching hook.
 *
 * Covers what this app needs -- load on mount, expose {data, error, loading},
 * refetch on demand, and abort in flight when the component unmounts or the
 * dependencies change. A caching library would add more than it earns here:
 * almost every screen loads once and the timed-test screens must NOT serve a
 * cached paper.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/api/client";

type State<T> = {
  data: T | null;
  error: ApiError | Error | null;
  loading: boolean;
};

export function useAsync<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: unknown[] = [],
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled ?? true;
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: enabled });

  // Keep the latest loader without making it a dependency, so callers can pass
  // an inline arrow function without causing an infinite refetch loop.
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const [nonce, setNonce] = useState(0);
  const refetch = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, error: null, loading: false });
      return;
    }

    const controller = new AbortController();
    let active = true;
    setState((previous) => ({ ...previous, loading: true, error: null }));

    loaderRef
      .current(controller.signal)
      .then((data) => {
        if (active) setState({ data, error: null, loading: false });
      })
      .catch((error: unknown) => {
        // An abort is a cancelled render, not a failure to report.
        if (!active || controller.signal.aborted) return;
        setState({
          data: null,
          error: error instanceof Error ? error : new Error("Something went wrong"),
          loading: false,
        });
      });

    return () => {
      active = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce, enabled]);

  return { ...state, refetch };
}
