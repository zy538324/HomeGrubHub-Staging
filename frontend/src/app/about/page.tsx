
import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function AboutPage() {
  return (
    <div className="container mx-auto my-10 space-y-16 px-4">
      <section className="text-center space-y-4">
        <h1 className="text-4xl font-bold">About HomeGrubHub</h1>
        <p className="text-lg text-muted-foreground">
          Revolutionizing how UK families plan meals, organize recipes, and
          help save money on groceries
        </p>
      </section>

      <section className="grid items-center gap-8 lg:grid-cols-2">
        <div className="space-y-6">
          <h2 className="text-2xl font-semibold">Our Mission</h2>
          <p className="text-lg">
            We believe every family deserves to eat well without breaking the
            budget or spending hours planning meals.
          </p>
          <p>
            HomeGrubHub was created to solve the daily challenge faced by
            millions of UK families: “What should we have for dinner?” Our
            intelligent meal planning system takes the stress out of meal
            preparation while helping you save money and reduce food waste.
          </p>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="flex items-center">
              <i className="fas fa-clock fa-2x text-blue-600 mr-3" />
              <div>
                <h5 className="mb-1 font-semibold">Save Time</h5>
                <small className="text-muted-foreground">
                  5+ hours weekly, organise and simplify meal planning
                </small>
              </div>
            </div>
            <div className="flex items-center">
              <i className="fas fa-leaf fa-2x text-green-600 mr-3" />
              <div>
                <h5 className="mb-1 font-semibold">Reduce Waste</h5>
                <small className="text-muted-foreground">
                  40% less food waste
                </small>
              </div>
            </div>
            <div className="flex items-center">
              <i className="fas fa-heart fa-2x text-red-600 mr-3" />
              <div>
                <h5 className="mb-1 font-semibold">Eat Better</h5>
                <small className="text-muted-foreground">
                  Nutritionally balanced
                </small>
              </div>
            </div>
          </div>
        </div>
        <div className="rounded bg-primary p-10 text-center text-primary-foreground shadow">
          <i className="fas fa-utensils fa-4x mb-3" />
          <h3 className="mb-3 text-2xl font-semibold">Smart Meal Planning</h3>
          <p className="mb-0">
            Join the revolution of UK families who have transformed their meal
            planning experience with HomeGrubHub
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-3xl">
        <div className="rounded bg-muted p-8 shadow">
          <h2 className="mb-4 text-center text-2xl font-semibold">Our Story</h2>
          <p>
            I started HomeGrubHub because, like many parents, I was constantly
            stressed about meal planning. Every week, I&apos;d spend hours browsing
            recipes, creating shopping lists, only to find myself throwing away
            unused ingredients and still asking &quot;what&apos;s for dinner?&quot;
          </p>
          <p>
            We at HomeGrubHub understand this struggle because we&apos;ve lived it.
            As busy parents ourselves, we experienced firsthand the daily
            challenge of trying to feed our families well while managing tight
            budgets and hectic schedules.
          </p>
          <p>
            What began as my personal solution to organize our family recipes
            has evolved into a platform that helps families like yours take
            control of meal planning, reduce waste, and actually enjoy cooking
            again.
          </p>
          <blockquote className="border-l-4 border-primary pl-4 mt-4 text-center">
            <p className="italic">
              &ldquo;We wanted to create a tool that would make healthy,
              budget-friendly meal planning accessible to every UK family,
              regardless of their cooking experience or budget constraints.&rdquo;
            </p>
            <footer className="mt-2 text-sm text-muted-foreground">
              HomeGrubHub Founding Team
            </footer>
          </blockquote>
        </div>
      </section>

      <section>
        <h2 className="mb-8 text-center text-2xl font-semibold">
          What Makes HomeGrubHub Special
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          <div className="rounded bg-card p-6 text-center shadow-sm">
            <i className="fas fa-brain fa-3x text-blue-600 mb-3" />
            <h4 className="mb-2 text-xl font-semibold">Smart AI Planning</h4>
            <p>
              Our intelligent system learns your preferences and suggests meals
              that fit your budget, dietary needs, and schedule.
            </p>
          </div>
          <div className="rounded bg-card p-6 text-center shadow-sm">
            <i className="fas fa-store fa-3x text-green-600 mb-3" />
            <h4 className="mb-2 text-xl font-semibold">UK Price Comparison</h4>
            <p>
              Real-time price data from major UK supermarkets helps you find
              the best deals and optimize your shopping budget.
            </p>
          </div>
          <div className="rounded bg-card p-6 text-center shadow-sm">
            <i className="fas fa-users fa-3x text-yellow-500 mb-3" />
            <h4 className="mb-2 text-xl font-semibold">Family-Focused</h4>
            <p>
              Designed specifically for UK families with features for different
              dietary needs, portion adjustments, and kid-friendly options.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-3xl">
        <h2 className="mb-8 text-center text-2xl font-semibold">Our Values</h2>
        <div className="grid gap-6 md:grid-cols-2">
          <div className="flex">
            <i className="fas fa-heart fa-2x text-red-600 mr-3 mt-1" />
            <div>
              <h4 className="text-lg font-semibold">Family First</h4>
              <p>
                Every feature we build is designed with real UK families in
                mind, solving actual problems faced in busy households.
              </p>
            </div>
          </div>
          <div className="flex">
            <i className="fas fa-shield-alt fa-2x text-green-600 mr-3 mt-1" />
            <div>
              <h4 className="text-lg font-semibold">Privacy &amp; Security</h4>
              <p>
                Your data is protected with bank-level security. We never sell
                your information or compromise your privacy.
              </p>
            </div>
          </div>
          <div className="flex">
            <i className="fas fa-lightbulb fa-2x text-yellow-500 mr-3 mt-1" />
            <div>
              <h4 className="text-lg font-semibold">Continuous Innovation</h4>
              <p>
                We&apos;re constantly improving our platform based on user
                feedback and the latest technology to serve you better.
              </p>
            </div>
          </div>
          <div className="flex">
            <i className="fas fa-handshake fa-2x text-blue-600 mr-3 mt-1" />
            <div>
              <h4 className="text-lg font-semibold">Community Support</h4>
              <p>
                We believe in the power of community and provide excellent
                support to help every family succeed.
              </p>
            </div>
        </div>
      </section>
    </div>
  )
}