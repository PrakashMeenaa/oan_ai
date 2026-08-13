import type { Metadata, Viewport } from "next"
import { Geist } from "next/font/google"
import "./globals.css"

const geist = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "OAN Group — AI Sales Consultant",
  description:
    "Talk to Aria, OAN Group's AI Sales Consultant. Get instant information about specialty chemicals, fertilizer additives, plasticizers, mining reagents, and logistics. Available in 10+ languages.",
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#09090b" },
  ],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${geist.variable} h-full`}>
      <body className="h-full bg-white dark:bg-zinc-950 text-zinc-950 dark:text-zinc-50">{children}</body>
    </html>
  )
}