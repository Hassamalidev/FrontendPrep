/**
 * Token storage.
 *
 * The backend issues JWTs in the response body rather than as httpOnly cookies,
 * so the browser has to hold them somewhere script-readable -- there is no
 * variant of this that is immune to XSS. What mitigates it is on the server:
 * refresh tokens rotate on every use, and presenting a rotated token revokes
 * the whole session family. A stolen token is therefore usable until the victim
 * next refreshes, not indefinitely.
 *
 * Kept in one module so that decision has exactly one place to change if the
 * API ever grows cookie auth.
 */

const ACCESS_KEY = "issb.access";
const REFRESH_KEY = "issb.refresh";

export type StoredTokens = {
  access_token: string;
  refresh_token: string;
};

/** Storage can throw in private mode or when site data is blocked. */
function safeGet(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* a session that cannot persist still works until reload */
  }
}

function safeRemove(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

export const tokens = {
  access: () => safeGet(ACCESS_KEY),
  refresh: () => safeGet(REFRESH_KEY),

  save(value: StoredTokens): void {
    safeSet(ACCESS_KEY, value.access_token);
    safeSet(REFRESH_KEY, value.refresh_token);
  },

  clear(): void {
    safeRemove(ACCESS_KEY);
    safeRemove(REFRESH_KEY);
  },

  has(): boolean {
    return Boolean(safeGet(ACCESS_KEY) && safeGet(REFRESH_KEY));
  },
};
