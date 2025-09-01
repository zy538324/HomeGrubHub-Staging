/* eslint-disable react/no-unescaped-entities */
import { Metadata } from "next"
import { Card, CardContent } from "@/components/ui/card"

export const metadata: Metadata = {
  title: "Privacy Policy",
}

export default function PrivacyPolicyPage() {
  const currentYear = new Date().getFullYear()
  return (
    <section className="container mx-auto py-10">
      <Card>
        <CardContent className="space-y-6">
          <h2 className="text-center text-3xl font-bold text-blue-600">
            Privacy Policy
          </h2>
          <p className="text-lg">
            This Privacy Policy explains how Home Grub Hub ("we", "us", or
            "our") collects, uses, discloses, and protects your personal data
            when you use Home Grub Hub (the "Service").
          </p>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">1. Information We Collect</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>
                <strong>Account Information:</strong> Name, email address,
                password (hashed), subscription type.
              </li>
              <li>
                <strong>Usage Data:</strong> Recipes saved or created, shopping
                list activity, nutrition tracking, community votes or
                contributions.
              </li>
              <li>
                <strong>Payment Details:</strong> Processed via Stripe. We do
                not store your full payment card information.
              </li>
              <li>
                <strong>Device &amp; Log Data:</strong> IP address, browser
                type, OS, timestamps, and interactions within the app.
              </li>
              <li>
                <strong>Cookies &amp; Tracking:</strong> See Section 6 for more
                on our cookie policy.
              </li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">2. How We Use Your Information</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>To operate and personalise your Home Grub Hub experience.</li>
              <li>To manage subscriptions and process payments securely.</li>
              <li>
                To improve the app’s performance, functionality, and
                recommendations.
              </li>
              <li>
                To send service-related messages, announcements, or billing
                notices.
              </li>
              <li>
                To comply with legal obligations and regulatory requirements.
              </li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">
              3. Legal Basis for Processing (UK GDPR)
            </h4>
            <p>We rely on the following lawful bases to process your personal data:</p>
            <ul className="list-disc space-y-1 pl-6">
              <li>
                <strong>Contract:</strong> To deliver the service you’ve
                requested.
              </li>
              <li>
                <strong>Consent:</strong> For optional communications, feature
                updates, and analytics cookies.
              </li>
              <li>
                <strong>Legal obligation:</strong> For record-keeping, fraud
                prevention, and compliance.
              </li>
              <li>
                <strong>Legitimate interests:</strong> To improve user experience
                and protect system integrity (only where your rights do not
                override our interest).
              </li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">4. Sharing Your Data</h4>
            <p>
              We never sell your personal data. However, we share necessary data
              with the following trusted providers:
            </p>
            <ul className="list-disc space-y-1 pl-6">
              <li>
                <strong>Auth0:</strong> Used for secure login, identity, and
                access management.
              </li>
              <li>
                <strong>Stripe:</strong> For handling all billing and payment
                operations.
              </li>
              <li>
                <strong>Analytics Providers (optional):</strong> Aggregated,
                anonymised data may be shared to help us understand usage
                patterns.
              </li>
              <li>
                All third parties are under contractual obligation to process
                your data securely and in compliance with UK data protection
                laws.
              </li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">5. Data Retention</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>We retain account data for as long as your account remains active.</li>
              <li>
                Upon deletion, your data is securely erased or anonymised within
                30 days, unless we are legally required to retain it.
              </li>
              <li>
                Usage data may be kept in anonymised form for analytical
                purposes beyond account deletion.
              </li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">6. Cookies &amp; Tracking</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>
                Essential cookies are used to maintain session security and core
                functionality.
              </li>
              <li>
                Optional cookies (analytics or feature tracking) are only used
                with your consent.
              </li>
              <li>
                You can manage your cookie preferences at any time in your
                browser settings or via our cookie banner.
              </li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">7. Your Rights</h4>
            <p>Under the UK GDPR, you have the following rights:</p>
            <ul className="list-disc space-y-1 pl-6">
              <li>Right to access – Request a copy of your personal data.</li>
              <li>
                Right to rectification – Correct inaccurate or incomplete data.
              </li>
              <li>
                Right to erasure – Request deletion of your data ("right to be
                forgotten").
              </li>
              <li>
                Right to restrict processing – Ask us to limit how we use your
                data.
              </li>
              <li>
                Right to data portability – Receive your data in a structured
                format.
              </li>
              <li>
                Right to object – Object to data processing under certain
                conditions.
              </li>
              <li>
                To exercise these rights, contact us at
                <a
                  href="mailto:support@homegrubhub.co.uk"
                  className="text-blue-600 underline"
                >
                  support@homegrubhub.co.uk
                </a>
                .
              </li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">8. Data Security</h4>
            <ul className="list-disc space-y-1 pl-6">
              <li>
                All data is encrypted in transit (HTTPS) and at rest (AES-256
                where applicable).
              </li>
              <li>
                We implement access controls, multi-factor authentication, and
                regular security audits.
              </li>
              <li>
                Despite our efforts, no system is 100% secure; we encourage
                strong passwords and 2FA where available.
              </li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">
              9. Data Transfers Outside the UK
            </h4>
            <p>
              Some of our service providers (e.g., Auth0 or Stripe) may process
              data outside the UK or EEA. In such cases, we ensure adequate
              safeguards, such as Standard Contractual Clauses (SCCs), are in
              place.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">10. Changes to This Policy</h4>
            <p>
              We may update this Privacy Policy to reflect legal or service
              changes. If changes are material, we will notify you via email or
              platform alerts. Continued use of the service after changes
              constitutes acceptance.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="text-xl font-semibold">11. Contact Us</h4>
            <p>
              If you have questions about this policy or how we process your data,
              please contact our Data Protection Officer:
            </p>
            <p>
              Email:
              <a
                href="mailto:support@homegrubhub.co.uk"
                className="text-blue-600 underline"
              >
                support@homegrubhub.co.uk
              </a>
              <br />
              Address: Home Grub Hub, 42 Market Street, Wellington, Somerset, UK
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
