"use client"

import { useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function OfflinePage() {
  useEffect(() => {
    function updateOnlineStatus() {
      if (navigator.onLine) {
        const banner = document.createElement("div")
        banner.className =
          "fixed top-0 left-1/2 -translate-x-1/2 mt-3 bg-green-600 text-white px-4 py-2 rounded shadow"
        banner.textContent = "You're back online!"
        document.body.appendChild(banner)
        setTimeout(() => {
          banner.remove()
          window.location.reload()
        }, 2000)
      }
    }

    function handleOffline() {
      console.log("HomeGrubHub: App is now offline")
    }

    window.addEventListener("online", updateOnlineStatus)
    window.addEventListener("offline", handleOffline)

    return () => {
      window.removeEventListener("online", updateOnlineStatus)
      window.removeEventListener("offline", handleOffline)
    }
  }, [])

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-4">
      <div className="min-h-[70vh] flex items-center justify-center text-center bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl my-8 p-12 text-white">
        <div className="space-y-6">
          <div className="text-5xl opacity-80 animate-pulse">📶</div>
          <h1 className="text-3xl font-bold">You&apos;re Offline</h1>
          <p className="text-lg opacity-90">
            Don&apos;t worry! You can still browse your saved recipes and use some features while offline.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="bg-white/20 border-2 border-white/30 text-white px-8 py-3 rounded-full font-semibold transition hover:bg-white/30 hover:border-white/50 hover:-translate-y-0.5"
          >
            Try Again
          </button>
          <div className="mt-8 bg-white/10 rounded-xl p-8 backdrop-blur">
            <h3 className="mb-4 font-semibold flex items-center justify-center gap-2">
              <span>✔</span> Available Offline
            </h3>
            <ul className="space-y-2">
              <li className="flex items-center justify-center gap-2"><span>🍽️</span>View your saved recipes</li>
              <li className="flex items-center justify-center gap-2"><span>❤️</span>Browse your favourites</li>
              <li className="flex items-center justify-center gap-2"><span>📝</span>Check your shopping lists</li>
              <li className="flex items-center justify-center gap-2"><span>📅</span>View meal plans</li>
            </ul>
          </div>
        </div>
      </div>

      <Card className="border-none shadow-sm">
        <CardHeader className="bg-muted">
          <CardTitle className="text-xl flex items-center gap-2">
            <span>⬇️</span> Recently Viewed Recipes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div id="offline-recipes" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Card className="h-full border-dashed">
              <CardContent className="flex flex-col items-center justify-center text-center text-muted-foreground h-full">
                <div className="text-2xl mb-3">🍳</div>
                <p>Your recently viewed recipes will appear here when cached</p>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

