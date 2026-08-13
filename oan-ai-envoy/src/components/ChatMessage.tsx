"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { Components } from "react-markdown"
import type { ChatMessage } from "@/types/chat"

interface ChatMessageProps {
  message: ChatMessage
}

const markdownComponents: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 dark:text-blue-400 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-sm"
    >
      {children}
    </a>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-2 rounded-lg border border-zinc-200 dark:border-zinc-700">
      <table className="min-w-full text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-zinc-50 dark:bg-zinc-800">{children}</thead>,
  th: ({ children }) => (
    <th className="px-3 py-2 text-left font-semibold text-zinc-700 dark:text-zinc-200 border-b border-zinc-200 dark:border-zinc-700">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-2 border-b border-zinc-100 dark:border-zinc-800 align-top">{children}</td>
  ),
}

export default function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-linear-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white text-xs font-bold mr-2 mt-1 shrink-0 shadow-sm ring-1 ring-inset ring-white/20">
          A
        </div>
      )}
      <div
        className={`max-w-[85%] sm:max-w-[78%] rounded-2xl px-4 py-3 text-[15px] leading-relaxed wrap-break-word ${
          isUser
            ? "bg-blue-600 text-white rounded-br-sm"
            : "bg-white dark:bg-zinc-900 text-zinc-950 dark:text-zinc-50 rounded-bl-sm shadow-sm border border-zinc-100 dark:border-zinc-800"
        }`}
        dir="auto"
      >
        {message.content ? (
          isUser ? (
            message.content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          )
        ) : (
          <span className="inline-flex gap-1 py-1">
            <span className="w-1.5 h-1.5 bg-zinc-400 dark:bg-zinc-500 rounded-full motion-safe:animate-bounce" />
            <span
              className="w-1.5 h-1.5 bg-zinc-400 dark:bg-zinc-500 rounded-full motion-safe:animate-bounce"
              style={{ animationDelay: "0.15s" }}
            />
            <span
              className="w-1.5 h-1.5 bg-zinc-400 dark:bg-zinc-500 rounded-full motion-safe:animate-bounce"
              style={{ animationDelay: "0.3s" }}
            />
          </span>
        )}
        {message.isStreaming && message.content && (
          <span className="ml-0.5 inline-block w-0.5 h-3.5 bg-zinc-400 dark:bg-zinc-500 motion-safe:animate-pulse align-middle" />
        )}
      </div>
    </div>
  )
}