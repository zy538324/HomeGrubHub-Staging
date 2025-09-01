import type { Metadata } from "next"
import "./globals.css"
import { Navbar } from "@/components/navbar"


export const metadata: Metadata = {
  title: {
    default: "HomeGrubHub - Smart Meal Planning & Recipe Organization App",
    template: "%s - HomeGrubHub",
  },
  description:
    "Plan meals, track nutrition, and organize recipes with HomeGrubHub.",
  keywords: [
    "meal planning app",
    "recipe organizer",
    "nutrition tracker",
    "grocery list generator",
    "meal prep planner",
    "healthy eating app",
    "family meal planning",
    "budget cooking",
  ],
  authors: [{ name: "HomeGrubHub" }],
  openGraph: {
    title: "HomeGrubHub - Smart Meal Planning & Recipe Organization App",
    description:
      "Plan meals, track nutrition, and organize recipes with HomeGrubHub.",
    url: "https://homegrubhub.com",
    siteName: "HomeGrubHub",
    locale: "en_GB",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "HomeGrubHub - Smart Meal Planning & Recipe Organization App",
    description:
      "Plan meals, track nutrition, and organize recipes with HomeGrubHub.",
    site: "@HomeGrubHub",
    creator: "@HomeGrubHub",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
          rel="stylesheet"
          crossOrigin="anonymous"
          referrerPolicy="no-referrer"
        />
      </head>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Navbar />
        {children}
        {/* Load bootstrap JS at end of body for interactive components (optional) */}
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
      </body>
    </html>
  )
}
