import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { Close, Logout, Menu, User } from "@/components/icons";
import { Button } from "@/components/ui";
import { useAuth } from "@/auth/useAuth";

const NAV = [
  { to: "/services", label: "Services" },
  { to: "/practice", label: "Practice" },
  { to: "/tests", label: "Mock Tests" },
  { to: "/issb", label: "ISSB Suite" },
  { to: "/articles", label: "Current Affairs" },
];

/** Shown only to signed-in students, so the public bar stays short. */
const MEMBER_NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/revision", label: "Revision" },
  { to: "/history", label: "My papers" },
];

export function Layout() {
  const { isAuthenticated, isStaff, user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-3 focus:rounded-lg focus:bg-army-500 focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>

      <header className="sticky top-0 z-40 border-b border-ink-200/70 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4">
          <Link to="/" className="flex items-center gap-2 font-display text-lg font-bold text-ink-900">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-army-500 text-sm font-bold text-white">
              FP
            </span>
            <span className="hidden sm:inline">Frontline Prep</span>
          </Link>

          <nav aria-label="Main" className="ml-4 hidden items-center gap-1 md:flex">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive ? "bg-army-50 text-army-600" : "text-ink-600 hover:bg-ink-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            {isAuthenticated ? (
              <>
                {isStaff && (
                  <NavLink
                    to="/admin"
                    className={({ isActive }) =>
                      `hidden rounded-lg px-3 py-2 text-sm font-medium sm:inline-block ${
                        isActive ? "bg-gold-50 text-ink-800" : "text-ink-600 hover:bg-ink-100"
                      }`
                    }
                  >
                    Admin
                  </NavLink>
                )}
                <NavLink
                  to="/dashboard"
                  className={({ isActive }) =>
                    `hidden rounded-lg px-3 py-2 text-sm font-medium sm:inline-block ${
                      isActive ? "bg-army-50 text-army-600" : "text-ink-600 hover:bg-ink-100"
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <Link
                  to="/profile"
                  className="hidden items-center gap-2 rounded-lg px-2 py-2 text-sm text-ink-600 hover:bg-ink-100 sm:flex"
                >
                  <User size={18} />
                  <span className="max-w-[10rem] truncate">{user?.full_name}</span>
                </Link>
                <Button variant="ghost" size="sm" onClick={() => void logout()} aria-label="Sign out">
                  <Logout size={18} />
                </Button>
              </>
            ) : (
              <>
                <Link to="/login" className="rounded-lg px-3 py-2 text-sm font-medium text-ink-600 hover:bg-ink-100">
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="rounded-lg bg-army-500 px-4 py-2 text-sm font-medium text-white hover:bg-army-600"
                >
                  Get started
                </Link>
              </>
            )}

            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              aria-expanded={menuOpen}
              aria-controls="mobile-nav"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? <Close size={20} /> : <Menu size={20} />}
            </Button>
          </div>
        </div>

        {menuOpen && (
          <nav id="mobile-nav" aria-label="Mobile" className="border-t border-ink-100 bg-white md:hidden">
            <div className="mx-auto max-w-6xl px-4 py-2">
              {[
                ...NAV,
                ...(isAuthenticated ? MEMBER_NAV : []),
                ...(isStaff ? [{ to: "/admin", label: "Admin" }] : []),
              ].map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMenuOpen(false)}
                  className={({ isActive }) =>
                    `block rounded-lg px-3 py-2.5 text-sm font-medium ${
                      isActive ? "bg-army-50 text-army-600" : "text-ink-700"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </nav>
        )}
      </header>

      <main id="main" className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-ink-200/70 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-ink-500 sm:flex-row sm:items-center sm:justify-between">
          <p>Frontline Prep — preparation for Army, Air Force and Navy selection.</p>
          <div className="flex gap-4">
            <Link to="/about" className="hover:text-ink-800">
              About
            </Link>
            <Link to="/articles" className="hover:text-ink-800">
              Current affairs
            </Link>
            <Link to="/contact" className="hover:text-ink-800">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
