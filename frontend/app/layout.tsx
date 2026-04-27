import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Geist_Mono, Noto_Sans, Plus_Jakarta_Sans } from "next/font/google";
import { ServiceWorkerRegister } from "@/components/ServiceWorkerRegister";
import "./globals.css";

/* NyayGuru-style marketing: friendly geometric sans + Noto for Hindi/Devanagari (e.g. /hi/*). */
const plusJakarta = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

const notoSans = Noto_Sans({
  variable: "--font-noto-sans",
  subsets: ["latin", "latin-ext", "devanagari"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

function publicSiteUrl(): string {
  const b = process.env.NEXT_PUBLIC_APP_URL?.trim();
  if (b) {
    try {
      return new URL(b).toString();
    } catch {
      // fall through
    }
  }
  return "http://localhost:3000";
}

export const metadata: Metadata = {
  // Avoid canonical / OG URLs using the App Runner host when the site is served at CloudFront (AllViewerExceptHost rewrites Host at origin)
  metadataBase: new URL(publicSiteUrl()),
  title: {
    default: "NyayaSetu — Legal clarity for India",
    template: "%s — NyayaSetu",
  },
  description:
    "Legal clarity for India — draft documents, understand your issue, and get practical next steps. Educational support, not a law firm.",
  applicationName: "NyayaSetu",
  themeColor: "#78350f",
  appleWebApp: {
    capable: true,
    title: "NyayaSetu",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        className={`${plusJakarta.variable} ${notoSans.variable} ${geistMono.variable} h-full scroll-smooth scroll-pt-20 antialiased`}
      >
        <body className="flex min-h-full flex-col font-sans antialiased">
          <ServiceWorkerRegister />
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
