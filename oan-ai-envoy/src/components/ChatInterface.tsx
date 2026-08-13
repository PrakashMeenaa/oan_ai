"use client";

import { useState, useRef, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import type { ChatMessage } from "@/types/chat";
import ChatMessageBubble from "./ChatMessage";
import { streamChatResponse, submitEnquiry as sendEnquiry, type HistoryMessage } from "@/lib/api";

const STORAGE_KEY = "oan-aria-chat-v1";

const INITIAL_MESSAGE: ChatMessage = {
  id: "aria-greeting",
  role: "assistant",
  content:
    "Hello! I'm Aria, OAN Group's AI Sales Consultant. I can help you with our specialty chemicals, fertilizer additives, plasticizers, mining reagents, and logistics services.\n\nYou can write to me in any language — English, Русский, Bahasa Indonesia, العربية, Français, हिन्दी, and more. How can I help you today?",
  isStreaming: false,
};

interface EnquiryForm {
  name: string;
  email: string;
  message: string;
}

type EnquiryStatus = "idle" | "sending" | "sent" | "error";

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [showEnquiry, setShowEnquiry] = useState(false);
  const [enquiryForm, setEnquiryForm] = useState<EnquiryForm>({
    name: "",
    email: "",
    message: "",
  });
  const [enquiryStatus, setEnquiryStatus] = useState<EnquiryStatus>("idle");
  const [fieldErrors, setFieldErrors] = useState<Partial<EnquiryForm>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed: ChatMessage[] = JSON.parse(saved);
        if (parsed.length > 0) {
          setMessages(parsed.map((msg) => ({ ...msg, isStreaming: false })));
        }
      }
    } catch {}
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    try {
      const toSave = messages.filter((m) => !m.isStreaming);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    } catch {}
  }, [messages, isLoaded]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const clearChat = () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
    setMessages([INITIAL_MESSAGE]);
  };

  const buildHistory = (currentMessages: ChatMessage[]): HistoryMessage[] =>
    currentMessages
      .filter((msg) => !msg.isStreaming && msg.content.length > 0)
      .slice(-16)
      .map((msg) => ({ role: msg.role, content: msg.content }));

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const history = buildHistory(messages);

    const userMessage: ChatMessage = {
      id: uuidv4(),
      role: "user",
      content: trimmed,
      isStreaming: false,
    };

    const assistantId = uuidv4();
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setInput("");
    setIsLoading(true);

    try {
      await streamChatResponse(
        trimmed,
        history,
        (token) => {
          setMessages((prev) => prev.map((msg) => (msg.id === assistantId ? { ...msg, content: msg.content + token } : msg)));
        },
        () => {
          setMessages((prev) => prev.map((msg) => (msg.id === assistantId ? { ...msg, isStreaming: false } : msg)));
          setIsLoading(false);
        },
      );
    } catch {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                content: "I'm having trouble connecting right now. Please try again in a moment.",
                isStreaming: false,
              }
            : msg,
        ),
      );
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const closeEnquiry = () => {
    setShowEnquiry(false);
    setEnquiryStatus("idle");
    setEnquiryForm({ name: "", email: "", message: "" });
    setFieldErrors({});
  };

  const handleEnquirySubmit = async () => {
    const errors: Partial<EnquiryForm> = {};

    if (!enquiryForm.email || !enquiryForm.email.includes("@")) {
      errors.email = "Please enter a valid email address";
    }
    if (!enquiryForm.message || enquiryForm.message.trim().length < 10) {
      errors.message = "Please describe your requirement (at least 10 characters)";
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setFieldErrors({});
    setEnquiryStatus("sending");

    try {
      const history = buildHistory(messages);
      await sendEnquiry(enquiryForm.name, enquiryForm.email, enquiryForm.message, history);
      setEnquiryStatus("sent");
    } catch {
      setEnquiryStatus("error");
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-4 py-3 flex items-center justify-between shadow-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">OAN</div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-semibold text-gray-900 text-sm">Aria — OAN Group Sales Consultant</p>
              <span className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-full font-medium border border-green-100">● Live</span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">Specialty Chemicals · Fertilizer Additives · Logistics · 10+ languages</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowEnquiry(true)} className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-full hover:bg-blue-700 transition-colors font-medium hidden sm:block">
            Send Enquiry
          </button>
          <button onClick={clearChat} className="text-xs text-gray-400 hover:text-gray-600 px-2.5 py-1.5 rounded-full hover:bg-gray-100 transition-colors">
            New Chat
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="max-w-3xl mx-auto">
          {messages.map((message) => (
            <ChatMessageBubble key={message.id} message={message} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="bg-white border-t px-4 py-3 flex-shrink-0">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-2 items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask in any language — English, Русский, Bahasa, العربية..."
              disabled={isLoading}
              className="flex-1 border border-gray-200 text-black rounded-full px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 disabled:opacity-50 bg-gray-50"
              dir="auto"
            />
            <button onClick={sendMessage} disabled={!input.trim() || isLoading} className="bg-blue-600 text-white rounded-full w-10 h-10 flex items-center justify-center disabled:opacity-40 hover:bg-blue-700 transition-colors flex-shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
              </svg>
            </button>
          </div>
          <div className="flex items-center justify-between mt-2">
            <p className="text-xs text-gray-400">info@oangroup.in · +91-141-4035484</p>
            <button onClick={() => setShowEnquiry(true)} className="text-xs text-blue-600 hover:underline sm:hidden">
              Send Enquiry →
            </button>
          </div>
        </div>
      </div>

      {/* Enquiry Modal */}
      {showEnquiry && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between p-5 border-b">
              <div>
                <h2 className="font-semibold text-gray-900">Send a Business Enquiry</h2>
                <p className="text-xs text-gray-500 mt-0.5">Our sales team will contact you within 24 hours</p>
              </div>
              <button onClick={closeEnquiry} className="text-gray-400 hover:text-gray-600 text-2xl leading-none w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100">
                ×
              </button>
            </div>

            {enquiryStatus === "sent" ? (
              <div className="p-8 text-center">
                <div className="w-14 h-14 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-green-100">
                  <svg className="w-7 h-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="font-semibold text-gray-900 text-lg">Enquiry Received!</p>
                <p className="text-sm text-gray-500 mt-1">
                  Our team will contact you at <span className="font-medium text-gray-700">{enquiryForm.email}</span> within 24 hours.
                </p>
                <button onClick={closeEnquiry} className="mt-5 text-sm bg-blue-600 text-white px-8 py-2.5 rounded-full hover:bg-blue-700 font-medium">
                  Done
                </button>
              </div>
            ) : (
              <div className="p-5 flex flex-col gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1.5 block">Your Name</label>
                  <input
                    type="text"
                    value={enquiryForm.name}
                    onChange={(e) => {
                      setEnquiryForm((prev) => ({ ...prev, name: e.target.value }));
                    }}
                    placeholder="Full name"
                    className="w-full border border-gray-200 text-black rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1.5 block">
                    Business Email <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="email"
                    value={enquiryForm.email}
                    onChange={(e) => {
                      setEnquiryForm((prev) => ({ ...prev, email: e.target.value }));
                      if (fieldErrors.email) {
                        setFieldErrors((prev) => ({ ...prev, email: undefined }));
                      }
                    }}
                    placeholder="you@company.com"
                    className={`w-full border rounded-xl px-3.5 text-black py-2.5 text-sm focus:outline-none transition-colors ${fieldErrors.email ? "border-red-400 bg-red-50 focus:border-red-500" : "border-gray-200 focus:border-blue-500"}`}
                  />
                  {fieldErrors.email && (
                    <p className="text-xs text-red-500 mt-1.5 flex items-center gap-1">
                      <span>⚠</span> {fieldErrors.email}
                    </p>
                  )}
                </div>

                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1.5 block">
                    Your Requirement <span className="text-red-400">*</span>
                  </label>
                  <textarea
                    value={enquiryForm.message}
                    onChange={(e) => {
                      setEnquiryForm((prev) => ({ ...prev, message: e.target.value }));
                      if (fieldErrors.message) {
                        setFieldErrors((prev) => ({ ...prev, message: undefined }));
                      }
                    }}
                    placeholder="Tell us about your requirement, quantity needed, industry, and any specific product you're interested in..."
                    rows={4}
                    className={`w-full border rounded-xl text-black px-3.5 py-2.5 text-sm focus:outline-none resize-none transition-colors ${fieldErrors.message ? "border-red-400 bg-red-50 focus:border-red-500" : "border-gray-200 focus:border-blue-500"}`}
                  />
                  {fieldErrors.message && (
                    <p className="text-xs text-red-500 mt-1.5 flex items-center gap-1">
                      <span>⚠</span> {fieldErrors.message}
                    </p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    {enquiryForm.message.length} characters
                    {enquiryForm.message.length < 10 && enquiryForm.message.length > 0 ? ` (${10 - enquiryForm.message.length} more needed)` : ""}
                  </p>
                </div>

                {enquiryStatus === "error" && (
                  <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                    <p className="text-sm text-red-700 font-medium">Submission failed</p>
                    <p className="text-xs text-red-500 mt-0.5">
                      Your enquiry could not be sent right now. Please email us directly at{" "}
                      <a href="mailto:info@oangroup.in" className="underline">
                        info@oangroup.in
                      </a>
                    </p>
                  </div>
                )}

                <button onClick={handleEnquirySubmit} disabled={enquiryStatus === "sending"} className="bg-blue-600 text-white py-3 rounded-xl text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
                  {enquiryStatus === "sending" ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Submitting...
                    </span>
                  ) : (
                    "Submit Enquiry"
                  )}
                </button>

                <p className="text-xs text-gray-400 text-center -mt-1">We typically respond within 24 business hours</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
