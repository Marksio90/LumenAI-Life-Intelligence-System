/**
 * Streaming Chat Utility
 * Handles Server-Sent Events (SSE) for real-time AI responses
 */

export interface StreamingOptions {
  onToken: (token: string) => void
  onComplete: (fullResponse: string) => void
  onError: (error: Error) => void
  onStart?: () => void
}

export interface ChatStreamMessage {
  user_id: string
  message: string
  conversationId?: string
}

/**
 * Creates a streaming chat connection using Server-Sent Events
 */
export async function streamChatResponse(
  message: ChatStreamMessage,
  options: StreamingOptions
): Promise<void> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const { onToken, onComplete, onError, onStart } = options

  let fullResponse = ''
  let controller: AbortController | null = null

  try {
    onStart?.()

    // Use fetch with ReadableStream for SSE
    controller = new AbortController()

    const response = await fetch(`${apiUrl}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify(message),
      signal: controller.signal
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('Response body is not readable')
    }

    const decoder = new TextDecoder()

    // Read stream
    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        break
      }

      // Decode chunk
      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()

          if (data === '[DONE]') {
            onComplete(fullResponse)
            return
          }

          try {
            const parsed = JSON.parse(data)

            if (parsed.type === 'token') {
              fullResponse += parsed.content
              onToken(parsed.content)
            } else if (parsed.type === 'error') {
              throw new Error(parsed.message)
            } else if (parsed.type === 'complete') {
              fullResponse = parsed.content
              onComplete(fullResponse)
              return
            }
          } catch (e) {
            // Skip invalid JSON
            console.warn('Failed to parse SSE data:', data)
          }
        }
      }
    }

    onComplete(fullResponse)
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        onError(new Error('Stream cancelled by user'))
      } else {
        onError(error)
      }
    } else {
      onError(new Error('Unknown streaming error'))
    }
  }
}

/**
 * Fallback to regular (non-streaming) chat if SSE not supported
 */
export async function regularChatResponse(
  message: ChatStreamMessage
): Promise<string> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const response = await fetch(`${apiUrl}/api/v1/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(message)
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const data = await response.json()
  return data.response || data.message || ''
}

/**
 * Smart chat function that tries streaming, falls back to regular
 */
export async function sendChatMessage(
  message: ChatStreamMessage,
  options: Partial<StreamingOptions> = {}
): Promise<string> {
  const isStreamingSupported =
    typeof window !== 'undefined' &&
    'ReadableStream' in window

  if (!isStreamingSupported) {
    // Fallback to regular chat
    return regularChatResponse(message)
  }

  return new Promise((resolve, reject) => {
    streamChatResponse(message, {
      onToken: options.onToken || (() => {}),
      onComplete: (response) => {
        options.onComplete?.(response)
        resolve(response)
      },
      onError: (error) => {
        options.onError?.(error)
        reject(error)
      },
      onStart: options.onStart
    })
  })
}

/**
 * Hook-style API for React components
 */
export class StreamingChatManager {
  private controller: AbortController | null = null

  async send(
    message: ChatStreamMessage,
    options: StreamingOptions
  ): Promise<void> {
    this.controller = new AbortController()
    return streamChatResponse(message, options)
  }

  cancel(): void {
    if (this.controller) {
      this.controller.abort()
      this.controller = null
    }
  }

  isActive(): boolean {
    return this.controller !== null
  }
}

/**
 * Typing effect simulator for smoother UI
 * Buffers tokens and displays them at consistent intervals
 */
export class TypingEffectBuffer {
  private buffer: string[] = []
  private intervalId: NodeJS.Timeout | null = null
  private onDisplay: (text: string) => void
  private displayedText: string = ''

  constructor(
    onDisplay: (text: string) => void,
    intervalMs: number = 30
  ) {
    this.onDisplay = onDisplay
    this.startInterval(intervalMs)
  }

  addToken(token: string): void {
    this.buffer.push(token)
  }

  private startInterval(ms: number): void {
    this.intervalId = setInterval(() => {
      if (this.buffer.length > 0) {
        // Display multiple tokens at once for smoother effect
        const tokensToDisplay = this.buffer.splice(0, 3).join('')
        this.displayedText += tokensToDisplay
        this.onDisplay(this.displayedText)
      }
    }, ms)
  }

  flush(): void {
    if (this.buffer.length > 0) {
      const remaining = this.buffer.join('')
      this.displayedText += remaining
      this.onDisplay(this.displayedText)
      this.buffer = []
    }
  }

  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
    }
    this.flush()
  }

  reset(): void {
    this.stop()
    this.buffer = []
    this.displayedText = ''
  }
}
