/**
 * The console's routes.
 *
 * Pages move here from Django one at a time (ADR-035, docs/spa-migration.md): each gets a route below, and
 * Django serves the console's index.html at the same path.
 */
import type { RouteObject } from "react-router";

import { HomePage } from "@/routes/HomePage";
import { Layout } from "@/routes/Layout";
import { LoginPage } from "@/routes/LoginPage";
import { NotFoundPage } from "@/routes/NotFoundPage";
import { PasswordResetPage } from "@/routes/PasswordResetPage";
import { PasswordResetRequestPage } from "@/routes/PasswordResetRequestPage";
import { RegisterPage } from "@/routes/RegisterPage";
import { RequireAuth } from "@/routes/RequireAuth";
import { LOGIN_PATH } from "@/lib/const";

export const routes: RouteObject[] = [
  // the pages of a visitor who isn't signed in.
  { path: LOGIN_PATH, element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  { path: "/password-reset-request", element: <PasswordResetRequestPage /> },
  // the path of the links in password reset emails, which Django served before the console did.
  { path: "/password-reset-link/:uidb64/:token", element: <PasswordResetPage /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <Layout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <HomePage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
