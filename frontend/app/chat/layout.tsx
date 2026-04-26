import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Assistant — NyayaSetu",
  description: "Chat, drafts, and next steps for your legal question.",
};

export default function ChatLayout({ children }: { children: ReactNode }) {
  return children;
}
