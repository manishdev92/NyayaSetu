import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Offline — NyayaSetu",
  description: "You appear to be offline.",
  robots: { index: false, follow: false },
};

export default function OfflinePage() {
  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col justify-center gap-6 px-6 py-16 text-stone-800">
      <div>
        <p className="text-sm font-medium uppercase tracking-wide text-amber-800/90">NyayaSetu</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-stone-900">You are offline</h1>
        <p className="mt-3 text-sm leading-relaxed text-stone-600">
          This page opens when there is no network. Reconnect to use the legal assistant, sign in, and call the API
          again.
        </p>
        <p className="mt-3 text-sm leading-relaxed text-stone-600" lang="hi">
          नेटवर्क नहीं है। कानूनी सहायक के लिए इंटरनेट जोड़ें और फिर से कोशिश करें।
        </p>
      </div>
      <Link
        href="/chat"
        className="inline-flex w-fit items-center justify-center rounded-xl bg-amber-800 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-900"
      >
        Try again
      </Link>
    </div>
  );
}
