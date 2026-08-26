/**
 * The context object, split from the provider component.
 *
 * A file that exports both a component and a non-component breaks React Fast
 * Refresh -- editing the provider then forces a full reload and drops the
 * session mid-development.
 */

import { createContext } from "react";

import type { LoginIn, RegisterIn, UserPublic } from "@/api/types";

export type AuthState = {
  user: UserPublic | null;
  /** True until the initial "am I signed in?" check settles. */
  loading: boolean;
  isAuthenticated: boolean;
  isStaff: boolean;
  login: (credentials: LoginIn) => Promise<UserPublic>;
  register: (details: RegisterIn) => Promise<UserPublic>;
  logout: () => Promise<void>;
  /** Replace the cached user after a profile save returns the fresh row. */
  applyUser: (user: UserPublic) => void;
};

export const AuthContext = createContext<AuthState | null>(null);
