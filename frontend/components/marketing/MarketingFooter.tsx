import Link from "next/link";
import { marketingBundle, mpath, type MarketingLocale } from "@/lib/marketingBundles";
import { NyayaSetuLogo, NyayaWordmark } from "./NyayaSetuLogo";

export function MarketingFooter({ locale }: { locale: MarketingLocale }) {
  const b = marketingBundle(locale);
  return (
    <footer className="border-t border-stone-200 bg-stone-50/90">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <div className="flex items-start gap-3">
              <NyayaSetuLogo className="h-10 w-10 shrink-0" aria-hidden />
              <div className="min-w-0">
                <NyayaWordmark className="text-base" />
                <p className="mt-1 text-sm font-medium text-stone-600">{b.brandTagline}</p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-stone-600">{b.disclaimerShort}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{b.chrome.product}</p>
            <ul className="mt-3 space-y-2">
              {b.nav.map((item) => (
                <li key={item.path}>
                  <Link href={mpath(locale, item.path)} className="text-sm text-stone-700 hover:text-amber-900">
                    {item.label}
                  </Link>
                </li>
              ))}
              <li>
                <Link href="/chat" className="text-sm text-stone-700 hover:text-amber-900">
                  {b.chrome.assistant}
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{b.chrome.account}</p>
            <ul className="mt-3 space-y-2">
              <li>
                <Link href="/dashboard" className="text-sm text-stone-700 hover:text-amber-900">
                  {b.chrome.dashboard}
                </Link>
              </li>
              <li>
                <Link href="/chat" className="text-sm text-stone-700 hover:text-amber-900">
                  {b.chrome.signInViaApp}
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{b.chrome.buildHost}</p>
            <p className="mt-3 text-sm leading-relaxed text-stone-600">{b.chrome.footerLegal}</p>
          </div>
        </div>
        <p className="mt-10 text-center text-xs text-stone-500">
          © {new Date().getFullYear()} NyayaSetu. {b.copyright}
        </p>
      </div>
    </footer>
  );
}
