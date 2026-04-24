import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Geist, Geist_Mono } from "next/font/google";
import { ServiceWorkerRegister } from "@/components/ServiceWorkerRegister";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
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
  title: "NyayaSetu — AI Legal Companion",
  description: "Draft documents, understand your issue, and get practical next steps.",
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
        className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      >
        <body className="flex min-h-full flex-col font-sans antialiased">
          <ServiceWorkerRegister />
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
