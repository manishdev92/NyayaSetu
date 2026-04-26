import type { ReactNode } from "react";

export default function HiMarketingLayout({ children }: { children: ReactNode }) {
  return <div className="contents">{children}</div>;
}
