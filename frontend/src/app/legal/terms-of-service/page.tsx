/* eslint-disable react/no-unescaped-entities */
import { Metadata } from "next"
import { Card, CardContent } from "@/components/ui/card"

export const metadata: Metadata = {
  title: "Terms of Service",
}

export default function TermsOfServicePage() {
  const currentYear = new Date().getFullYear()
  return (
    <section className="container mx-auto py-10">
      <Card>
        <CardContent className="space-y-6">
          <h2 className="text-center text-3xl font-bold text-blue-600">
            Terms of Service
          </h2>
          <p className="text-lg">
            These Terms of Service ("Terms") govern your use of Home Grub Hub,
            a web-based application operated by Home Grub Hub ("we", "us", or
            "our"). By creating an account or using any part of the Home Grub
            Hub platform, you agree to be bound by these Terms.
          </p>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">1. Eligibility &amp; Account Registration</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>You must be at least 18 years of age or the age of majority in your jurisdiction.</li>
              <li>You agree to provide accurate, current, and complete information during registration and to keep it updated.</li>
              <li>You are responsible for maintaining the confidentiality of your account and password and for all activity under your account.</li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">2. Description of Service</h4>
            <p>
              Home Grub Hub provides tools for meal planning, recipe storage, nutritional tracking, shopping list generation, and community recipe sharing and voting. Features may vary depending on your subscription tier.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">3. Subscription Plans &amp; Billing</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>Home Grub Hub offers both free and paid subscription tiers. Paid plans are billed via Stripe in GBP (£) on a monthly basis.</li>
              <li>By subscribing to a paid plan, you authorise us to charge your payment method on a recurring basis until cancellation.</li>
              <li>You may cancel your subscription at any time from your account settings. Access to paid features will continue until the end of the billing cycle.</li>
              <li>Refunds are not guaranteed and are granted only at our sole discretion, in accordance with our <a href="/refund-policy" className="text-blue-600 underline">Refund Policy</a>.</li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">4. Acceptable Use Policy</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>You agree not to use Home Grub Hub for any unlawful, harmful, or abusive activity.</li>
              <li>You may not upload, post, or share content that is offensive, misleading, or infringes on the rights of others.</li>
              <li>Automated access, scraping, or use of the API without written permission is strictly prohibited.</li>
              <li>We reserve the right to suspend or terminate accounts that breach our Acceptable Use Policy or these Terms.</li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">5. Intellectual Property</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>All content provided by us on the Home Grub Hub platform (excluding user-submitted content) is our intellectual property and is protected by copyright, trademark, and other laws.</li>
              <li>You retain rights to your submitted recipes and content. However, by posting content to Home Grub Hub, you grant us a non-exclusive, royalty-free licence to use, display, and distribute that content within the platform.</li>
              <li>Reproduction or resale of our services or branding without permission is prohibited.</li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">6. Community Contributions</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>Users may contribute recipes, comments, and nutritional data to the community.</li>
              <li>We reserve the right to moderate, remove, or flag user-submitted content that violates our guidelines or Terms.</li>
              <li>Users are solely responsible for the content they upload.</li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">7. Data Protection &amp; Privacy</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>We are committed to protecting your data in accordance with UK GDPR and the Data Protection Act 2018.</li>
              <li>Details on how we collect, store, and process your data are outlined in our <a href="/legal/privacy-policy" className="text-blue-600 underline">Privacy Policy</a>.</li>
              <li>We may use aggregated, anonymised data for analytical or feature-improvement purposes.</li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">8. Downtime &amp; Service Availability</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>Home Grub Hub is offered "as-is" and "as-available". We strive for high availability but do not guarantee uninterrupted service.</li>
              <li>Planned maintenance or unforeseen outages may temporarily affect access to the platform.</li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">9. Termination</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>You may terminate your account at any time via your account dashboard.</li>
              <li>We reserve the right to suspend or terminate accounts at our discretion if these Terms are breached or for suspected misuse.</li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">10. Limitation of Liability</h4>
            <p>
              To the extent permitted by law, Home Grub Hub shall not be liable for indirect, incidental, or consequential damages resulting from the use or inability to use the Home Grub Hub service.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">11. Changes to These Terms</h4>
            <p>
              We may revise these Terms periodically. Material changes will be communicated via email or platform notice. Continued use after changes indicates acceptance of the revised Terms.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">12. Contact</h4>
            <p>
              If you have any questions or concerns about these Terms, contact us at
              <a href="mailto:support@homegrubhub.co.uk" className="text-blue-600 underline"> support@homegrubhub.co.uk</a>.
            </p>
          </div>

          <hr className="my-4" />
          <p className="text-center text-sm text-gray-500">
            &copy; {currentYear} Home Grub Hub. All rights reserved.
          </p>
        </CardContent>
      </Card>
    </section>
  )
}

