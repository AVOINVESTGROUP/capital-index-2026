import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CAPITAL INDEX Admin",
  description: "Operator console for CAPITAL INDEX 2026",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
