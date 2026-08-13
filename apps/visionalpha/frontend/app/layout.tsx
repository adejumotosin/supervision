import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VisionAlpha | Alternative Data Intelligence",
  description: "Computer vision powered alternative data and investment intelligence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
