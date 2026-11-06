/** The frame of the sign-in pages: the logo, a title, and the page's form, centered on the page. */
import type { ReactNode } from "react";

import { useConsoleSession } from "@/session/context";

export function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  const { session } = useConsoleSession();
  return (
    <main className="d-flex flex-column align-items-center justify-content-center min-vh-100 p-6">
      <div className="card shadow-sm w-100" style={{ maxWidth: "28rem" }}>
        <div className="card-body p-10">
          {session && (
            <div className="text-center mb-6">
              <img src={session.branding.logoUrl} alt={session.branding.productName} height={48} />
            </div>
          )}
          <h1 className="fs-2 fw-bold text-center mb-8">{title}</h1>
          {children}
        </div>
      </div>
    </main>
  );
}
