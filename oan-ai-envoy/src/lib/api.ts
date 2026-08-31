const API_URL = process.env.NEXT_PUBLIC_API_URL

export interface HistoryMessage {
  role: "user" | "assistant"
  content: string
}

export async function streamChatResponse(
  message: string,
  history: HistoryMessage[],
  onToken: (token: string) => void,
  onDone: () => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  })

  if (response.status === 429) {
    throw new Error("RATE_LIMITED")
  }

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n")
    buffer = lines.pop() ?? ""

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue
      const payload = line.slice(6)
      if (payload.trim() === "[DONE]") {
        onDone()
        return
      }
      if (!payload) continue
      try {
        const token = JSON.parse(payload) as string
        if (token) {
          onToken(token)
        }
      } catch {
        continue
      }
    }
  }
}
export async function submitEnquiry(
  name: string,
  email: string,
  message: string,
  chatHistory: HistoryMessage[]
): Promise<void> {
  const response = await fetch(`${API_URL}/api/enquiry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      email,
      message,
      chat_history: chatHistory,
    }),
  })
  if (!response.ok) throw new Error("Enquiry failed")
}