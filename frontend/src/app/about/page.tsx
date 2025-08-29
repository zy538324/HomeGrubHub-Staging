import { Button } from "@/components/ui/button"
import Link from "next/link"

export default function AboutPage() {
  return (
    <div className="space-y-16">
      <section className="text-center space-y-4">
        <h1 className="text-4xl font-bold">About HomeGrubHub</h1>
        <p className="text-lg text-muted-foreground">
          Revolutionizing how UK families plan meals, organize recipes, and help save money on groceries
        </p>
      </section>

      <section className="grid gap-8 md:grid-cols-2 items-center">
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold">Our Mission</h2>
          <p className="text-lg">
            We believe every family deserves to eat well without breaking the budget or spending hours planning meals.
          </p>
          <p>
            HomeGrubHub was created to solve the daily challenge faced by millions of UK families: “What should we have for dinner?” Our intelligent meal planning system takes the stress out of meal preparation while helping you save money and reduce food waste.
          </p>
        </div>
        <div className="rounded bg-primary text-primary-foreground p-10 text-center">
          <h3 className="mb-3 text-2xl font-semibold">Smart Meal Planning</h3>
          <p className="mb-0">Join the revolution of UK families who have transformed their meal planning experience with HomeGrubHub.</p>
        </div>
      </section>

      <section className="max-w-3xl mx-auto space-y-4">
        <h2 className="text-2xl font-semibold text-center">Our Values</h2>
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="font-semibold">Family First</h3>
            <p>Every feature we build is designed with real UK families in mind, solving actual problems faced in busy households.</p>
          </div>
          <div>
            <h3 className="font-semibold">Privacy & Security</h3>
            <p>Your data is protected with bank-level security. We never sell your information or compromise your privacy.</p>
          </div>
          <div>
            <h3 className="font-semibold">Continuous Innovation</h3>
            <p>We&apos;re constantly improving our platform based on user feedback and the latest technology to serve you better.</p>
          </div>
          <div>
            <h3 className="font-semibold">Community Support</h3>
            <p>We believe in the power of community and provide excellent support to help every family succeed.</p>
          </div>
        </div>
      </section>

      <section className="max-w-3xl mx-auto text-center space-y-4">
        <h2 className="text-2xl font-semibold">Get in Touch</h2>
        <p>Have questions, suggestions, or just want to say hello? We&apos;d love to hear from you!</p>
        <div className="flex justify-center gap-4">
          <Button asChild>
            <Link href="/support/contact">Contact Support</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/community">Join Community</Link>
          </Button>
        </div>
      </section>
    </div>
  )
}
