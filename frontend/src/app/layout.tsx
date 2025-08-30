import type { Metadata } from "next"
import "./globals.css"
import { Navbar } from "@/components/navbar"

export const metadata: Metadata = {
  title: {
    default: "HomeGrubHub - Smart Meal Planning & Recipe Organization App",
    template: "%s - HomeGrubHub",
  },
  description: "Plan meals, track nutrition, and organize recipes with HomeGrubHub.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background font-sans antialiased">
        <Navbar />
        {children}
      </body>
    </html>
  )
}
