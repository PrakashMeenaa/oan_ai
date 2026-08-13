"use client"

import type { ChatMessage } from "@/types/chat"

interface ChatMessageProps {
  message: ChatMessage
}

export default function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold mr-2 mt-1 flex-shrink-0">
          A
        </div>
      )}
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed break-words ${
          isUser
            ? "bg-blue-600 text-white rounded-br-sm"
            : "bg-white text-gray-900 rounded-bl-sm shadow-sm border border-gray-100"
        }`}
        dir="auto"
      >
        {message.content || (
          <span className="inline-flex gap-1 py-1">
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.15s" }} />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.3s" }} />
          </span>
        )}
        {message.isStreaming && message.content && (
          <span className="ml-0.5 inline-block w-0.5 h-3.5 bg-gray-400 animate-pulse align-middle" />
        )}
      </div>
    </div>
  )
}