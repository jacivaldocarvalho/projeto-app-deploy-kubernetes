import { useRef, useState, type FormEvent } from 'react'

type Status = 'idle' | 'sending' | 'success' | 'error'
const unavailable = 'Unable to save the message. Please try again later.'

export default function App() {
  const [status, setStatus] = useState<Status>('idle')
  const [message, setMessage] = useState('')
  const sending = useRef(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (sending.current) return
    const form = event.currentTarget
    if (!form.reportValidity()) return
    const data = new FormData(form)
    const payload = new URLSearchParams()
    for (const name of ['nome', 'email', 'comentario']) {
      const value = String(data.get(name) ?? '').trim()
      if (!value) { setStatus('error'); setMessage('Please complete all fields.'); return }
      payload.set(name, value)
    }
    sending.current = true
    setStatus('sending')
    setMessage('Sending your message…')
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 10000)
    try {
      const response = await fetch('/index.php', { method: 'POST', body: payload, signal: controller.signal })
      const body = await response.text()
      if (!response.ok) { setStatus('error'); setMessage(response.status === 422 ? body : unavailable); return }
      if (body.trim() !== 'New record created successfully') throw new Error('Unexpected response')
      form.reset()
      setStatus('success')
      setMessage('Message saved successfully. Thank you for getting in touch.')
    } catch { setStatus('error'); setMessage(unavailable) }
    finally { window.clearTimeout(timeout); sending.current = false }
  }
  return (
    <main className="page">
      <section className="contact" aria-labelledby="contact-title">
        <div className="intro">
          <a className="brand" href="/" aria-label="Contact form home"><span className="brand-mark">C</span> Contact</a>
          <div className="intro-copy">
            <p className="eyebrow">LET’S CONNECT</p>
            <h1 id="contact-title">A conversation<br />starts here.</h1>
            <p className="description">Have a question or an idea to share? Leave a message. We’d love to hear from you.</p>
          </div>
          <p className="intro-footer">A little hello can go a long way.</p>
        </div>
        <div className="form-panel">
          <p className="eyebrow">GET IN TOUCH</p>
          <h2>Send a message</h2>
          <p className="form-description">Tell us what’s on your mind. All fields are required.</p>
          <form method="post" action="/index.php" onSubmit={submit} aria-busy={status === 'sending'}>
            <fieldset disabled={status === 'sending'}>
              <label htmlFor="name">Your name</label>
              <input id="name" name="nome" autoComplete="name" placeholder="How should we call you?" required maxLength={50} />
              <label htmlFor="email">Email address</label>
              <input id="email" name="email" type="email" autoComplete="email" placeholder="you@example.com" required maxLength={50} />
              <div className="field-heading"><label htmlFor="comment">Your message</label><span>Up to 100 characters</span></div>
              <textarea id="comment" name="comentario" placeholder="What would you like to share?" required maxLength={100} rows={4} />
              <button type="submit">{status === 'sending' ? 'Sending…' : 'Send message'}<span aria-hidden="true">↗</span></button>
            </fieldset>
            <div className={`feedback ${status}`} role={status === 'error' ? 'alert' : 'status'} aria-live={status === 'error' ? 'assertive' : 'polite'}>{message}</div>
          </form>
          <p className="privacy">Please avoid sharing passwords or other sensitive information.</p>
        </div>
      </section>
      <footer className="page-footer">Contact Form <span aria-hidden="true">·</span> Built for connection</footer>
    </main>
  )
}
