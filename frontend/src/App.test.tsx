import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

function fill() {
  fireEvent.change(screen.getByLabelText('Your name'), { target: { value: ' Test User ' } })
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'user@example.com' } })
  fireEvent.change(screen.getByLabelText('Your message'), { target: { value: 'Hello' } })
}
function response(status: number, body: string) {
  return { ok: status === 200, status, text: async () => body }
}

describe('Contact form', () => {
  it('exposes labels, field limits and native email validation', () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    expect(screen.getByLabelText('Your name')).toHaveAttribute('maxlength', '50')
    expect(screen.getByLabelText('Your message')).toHaveAttribute('maxlength', '100')
    fill()
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'invalid' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Send message' }).closest('form')!)
    expect(fetch).not.toHaveBeenCalled()
  })
  it('rejects whitespace-only fields without a request', () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    fill()
    fireEvent.change(screen.getByLabelText('Your name'), { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Please complete all fields.')
    expect(fetch).not.toHaveBeenCalled()
  })
  it('sends the existing form contract and clears fields only on success', async () => {
    const fetch = vi.fn().mockResolvedValue(response(200, 'New record created successfully'))
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    fill()
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText(/Message saved successfully/)
    const [path, options] = fetch.mock.calls[0]
    expect(path).toBe('/index.php')
    expect(options.method).toBe('POST')
    expect(Object.fromEntries(options.body)).toEqual({ nome: 'Test User', email: 'user@example.com', comentario: 'Hello' })
    expect(screen.getByLabelText('Your name')).toHaveValue('')
  })
  it('disables fields and prevents duplicate submissions while sending', async () => {
    let finish!: (value: ReturnType<typeof response>) => void
    const fetch = vi.fn().mockReturnValue(new Promise(resolve => { finish = resolve }))
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    fill()
    const form = screen.getByRole('button', { name: 'Send message' }).closest('form')!
    fireEvent.submit(form)
    fireEvent.submit(form)
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Sending…' })).toBeDisabled()
    expect(screen.getByLabelText('Your name')).toBeDisabled()
    finish(response(200, 'New record created successfully'))
    await screen.findByText(/Message saved successfully/)
  })
  it.each([
    [422, 'Invalid email address', 'Invalid email address'],
    [503, 'Internal details', 'Unable to save the message. Please try again later.'],
    [200, '<html>Unexpected response</html>', 'Unable to save the message. Please try again later.'],
  ])('handles HTTP %s without resetting input', async (status, body, expected) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(status, body)))
    render(<App />)
    fill()
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(expected)
    expect(screen.getByLabelText('Your message')).toHaveValue('Hello')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Send message' })).toBeEnabled())
  })
  it('handles a network failure without losing the message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network failure')))
    render(<App />)
    fill()
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to save the message.')
    expect(screen.getByLabelText('Your message')).toHaveValue('Hello')
  })
})
