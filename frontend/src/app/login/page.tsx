import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"

export default function LoginPage() {
  return (
    <main className="container py-5">
      <div className="row justify-content-center">
        <div className="col-md-6 col-lg-5">
          <Card className="shadow-sm border-0">
            <div className="card-body p-4">
              <h2 className="mb-4 text-center text-primary">Sign In</h2>
              {/* We'll submit this form to the Flask backend at /login */}
              <form id="flask-login-form" action="http://localhost:8050/login" method="post" noValidate>
                <input type="hidden" name="csrf_token" id="csrf_token_hidden" />
                <div className="mb-3">
                  <Label htmlFor="username">Username</Label>
                  <Input id="username" name="username" className="form-control form-control-lg" type="text" required />
                </div>
                <div className="mb-3">
                  <Label htmlFor="password">Password</Label>
                  <Input id="password" name="password" className="form-control form-control-lg" type="password" required />
                </div>
                <div className="mb-3 form-check">
                  <input className="form-check-input" type="checkbox" id="remember_me" name="remember_me" />
                  <label className="form-check-label" htmlFor="remember_me">Remember Me</label>
                </div>
                <div className="d-grid">
                  <Button asChild>
                    <button type="submit" className="btn btn-primary btn-lg w-100">Sign In</button>
                  </Button>
                </div>
              </form>
              <div className="mt-3 text-center">
                <a href="/register" className="text-decoration-none">New user? Register here</a>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <script dangerouslySetInnerHTML={{ __html: `
        // Fetch CSRF token from Flask login page and populate the hidden input so server-side validation passes
        (async function() {
          try {
            const res = await fetch('http://localhost:8050/login', { cache: 'no-store' });
            const text = await res.text();
            const doc = new DOMParser().parseFromString(text, 'text/html');
            const tokenInput = doc.querySelector('input[name="csrf_token"]');
            if (tokenInput) {
              const token = tokenInput.value;
              const hidden = document.getElementById('csrf_token_hidden');
              if (hidden) hidden.value = token;
            }
          } catch (e) {
            console.warn('Could not fetch CSRF token from Flask backend:', e);
          }
        })();
      ` }} />
    </main>
  )
}
