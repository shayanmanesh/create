import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Create.ai - AI-Powered Content Creation",
  description: "Transform your ideas into viral content in under 30 seconds with AI",
  keywords: "AI, content creation, viral, challenges, social media",
  openGraph: {
    title: "Create.ai - AI-Powered Content Creation",
    description: "Transform your ideas into viral content in under 30 seconds",
    images: ["/og-image.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "Create.ai - AI-Powered Content Creation",
    description: "Transform your ideas into viral content in under 30 seconds",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased bg-black text-white`}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
