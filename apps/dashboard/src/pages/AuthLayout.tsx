import type { ReactNode } from "react";

export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div
            aria-hidden="true"
            className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600 text-lg font-bold text-white"
          >
            SC
          </div>
          <p className="text-sm font-medium text-gray-500">AI Space Chameleon</p>
          <h1 className="mt-1 text-2xl font-semibold text-gray-900">{title}</h1>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">{children}</div>
      </div>
    </main>
  );
}
