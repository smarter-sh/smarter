/**
 * The console's routes.
 *
 * Pages move here from Django one at a time (ADR-035, docs/spa-migration.md): each gets a route below, and
 * Django serves the console's index.html at the same path.
 */
import { Navigate, type RouteObject } from "react-router";

import { ActivatePage } from "@/routes/ActivatePage";
import { AlreadyAssociatedPage } from "@/routes/AlreadyAssociatedPage";
import { InactivePage } from "@/routes/InactivePage";
import { Layout } from "@/routes/Layout";
import { LoginPage } from "@/routes/LoginPage";
import { NotFoundPage } from "@/routes/NotFoundPage";
import { PasswordResetPage } from "@/routes/PasswordResetPage";
import { PasswordResetRequestPage } from "@/routes/PasswordResetRequestPage";
import { RegisterPage } from "@/routes/RegisterPage";
import { RequireAuth } from "@/routes/RequireAuth";
import { DASHBOARD_PATH, INACTIVE_PATH, LOGIN_PATH } from "@/lib/const";
import { LIST_PAGES, type ListPage as ListPageConfig } from "@/lib/lists";

/** A list's route: its package loads in a chunk of its own, when the list is first opened. */
function listRoute(page: ListPageConfig): RouteObject {
  return {
    path: page.path,
    lazy: async () => {
      const [{ ListPage }, List] = await Promise.all([import("@/routes/ListPage"), page.load()]);
      return { Component: () => <ListPage page={page} List={List} /> };
    },
  };
}

export const routes: RouteObject[] = [
  // the pages of a visitor who isn't signed in.
  { path: LOGIN_PATH, element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  { path: "/password-reset-request", element: <PasswordResetRequestPage /> },
  // the path of the links in password reset emails, which Django served before the console did.
  { path: "/password-reset-link/:uidb64/:token", element: <PasswordResetPage /> },
  // the path of the links in activation emails.
  { path: "/account/activate/:uidb64/:token", element: <ActivatePage /> },
  // the social sign-in pipeline redirects to these two.
  { path: INACTIVE_PATH, element: <InactivePage /> },
  { path: "/account/already-associated", element: <AlreadyAssociatedPage /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <Layout />
      </RequireAuth>
    ),
    children: [
      // the dashboard is the console's home.
      { index: true, element: <Navigate to={DASHBOARD_PATH} replace /> },
      {
        path: DASHBOARD_PATH,
        // the dashboard and its widgets load in a chunk of their own, which the sign-in pages don't need.
        lazy: async () => ({ Component: (await import("@/routes/DashboardPage")).DashboardPage }),
      },
      ...LIST_PAGES.map(listRoute),
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
