import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RivalScope | Competitive intelligence",
  description: "Multi-agent competitive intelligence for fintech teams.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
