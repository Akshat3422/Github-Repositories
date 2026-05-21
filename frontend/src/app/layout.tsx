import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Developer Story Extraction Platform",
  description: "Convert your GitHub repositories into engaging, professional LinkedIn posts using a multi-agent AI pipeline.",
};

export default function RootLayout({
  children,
}: Readtype = Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen text-slate-100 bg-black selection:bg-violet-600 selection:text-white">
        <div className="glow-bg" />
        {children}
      </body>
    </html>
  );
}
