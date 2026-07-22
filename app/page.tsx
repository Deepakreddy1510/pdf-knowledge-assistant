"use client";

import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";


type MessageRole = "user" | "assistant";


type Message = {
  id: string;
  role: MessageRole;
  content: string;
};


type Source = {
  number: number;
  page: number | null;
  source: string;
  similarity: number | null;
  content: string;
};


type ChatApiResponse = {
  answer?: string;
  sources?: Source[];
  error?: string;
  details?: string;
};


const STARTER_QUESTIONS = [
  "What are the symptoms of pellagra?",
  "How often should infants be breastfed?",
  "How does saliva help with digestion?",
  "What are micronutrients?",
];


function createMessage(
  role: MessageRole,
  content: string,
): Message {
  return {
    id: crypto.randomUUID(),
    role,
    content,
  };
}


export default function Home() {
  const [input, setInput] = useState("");

  const [messages, setMessages] = useState<Message[]>([
    createMessage(
      "assistant",
      "Hello! Ask me a nutrition-related question. " +
        "I will search the Human Nutrition textbook and answer using the retrieved document context.",
    ),
  ]);

  const [sources, setSources] = useState<Source[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const messagesEndRef =
    useRef<HTMLDivElement | null>(null);


  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, busy]);


  async function send(
    predefinedQuestion?: string,
  ): Promise<void> {
    const message =
      predefinedQuestion?.trim() || input.trim();

    if (!message || busy) {
      return;
    }

    setInput("");
    setError("");
    setSources([]);
    setBusy(true);

    setMessages((currentMessages) => [
      ...currentMessages,
      createMessage("user", message),
    ]);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
        }),
      });

      const data =
        (await response.json()) as ChatApiResponse;

      if (!response.ok) {
        throw new Error(
          data.details ||
            data.error ||
            "The chat request failed.",
        );
      }

      const answer =
        data.answer?.trim() ||
        "I could not generate an answer.";

      setMessages((currentMessages) => [
        ...currentMessages,
        createMessage("assistant", answer),
      ]);

      setSources(data.sources ?? []);
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "An unexpected error occurred.";

      setError(message);

      setMessages((currentMessages) => [
        ...currentMessages,
        createMessage(
          "assistant",
          "Sorry, I could not process that question. " +
            "Please check the server terminal for details and try again.",
        ),
      ]);
    } finally {
      setBusy(false);
    }
  }


  function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): void {
    event.preventDefault();
    void send();
  }


  function handleKeyDown(
    event: KeyboardEvent<HTMLTextAreaElement>,
  ): void {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      void send();
    }
  }


  function clearConversation(): void {
    if (busy) {
      return;
    }

    setMessages([
      createMessage(
        "assistant",
        "Conversation cleared. Ask another question about the Human Nutrition textbook.",
      ),
    ]);

    setSources([]);
    setError("");
    setInput("");
  }


  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col">
        <header className="border-b border-slate-800 bg-slate-950/90 px-5 py-4 backdrop-blur sm:px-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-500 text-xl font-bold text-slate-950">
                  N
                </div>

                <div>
                  <h1 className="text-lg font-semibold sm:text-xl">
                    Nutrition RAG Assistant
                  </h1>

                  <p className="text-xs text-slate-400 sm:text-sm">
                    Supabase pgvector · MiniLM · Gemini
                  </p>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={clearConversation}
              disabled={busy}
              className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Clear chat
            </button>
          </div>
        </header>

        <div className="grid flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px]">
          <section className="flex min-h-0 flex-col border-slate-800 lg:border-r">
            <div className="flex-1 space-y-6 overflow-y-auto px-4 py-6 sm:px-8">
              {messages.map((message) => {
                const isUser =
                  message.role === "user";

                return (
                  <div
                    key={message.id}
                    className={`flex ${
                      isUser
                        ? "justify-end"
                        : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[88%] rounded-2xl px-4 py-3 shadow-sm sm:max-w-[78%] sm:px-5 sm:py-4 ${
                        isUser
                          ? "rounded-br-md bg-emerald-500 text-slate-950"
                          : "rounded-bl-md border border-slate-800 bg-slate-900 text-slate-100"
                      }`}
                    >
                      <div className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-70">
                        {isUser
                          ? "You"
                          : "Nutrition Assistant"}
                      </div>

                      <p className="whitespace-pre-wrap text-sm leading-7 sm:text-base">
                        {message.content}
                      </p>
                    </div>
                  </div>
                );
              })}

              {busy && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-bl-md border border-slate-800 bg-slate-900 px-5 py-4">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Nutrition Assistant
                    </div>

                    <div className="flex items-center gap-2 text-sm text-slate-300">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-400 [animation-delay:-0.3s]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-400 [animation-delay:-0.15s]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-400" />
                      <span className="ml-1">
                        Searching the textbook...
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {error && (
                <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  <span className="font-semibold">
                    Request error:
                  </span>{" "}
                  {error}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-slate-800 bg-slate-950 px-4 py-4 sm:px-8">
              {messages.length <= 1 && (
                <div className="mb-4 flex flex-wrap gap-2">
                  {STARTER_QUESTIONS.map(
                    (question) => (
                      <button
                        key={question}
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          void send(question);
                        }}
                        className="rounded-full border border-slate-700 bg-slate-900 px-3 py-2 text-left text-xs text-slate-300 transition hover:border-emerald-500/60 hover:text-emerald-300 disabled:opacity-50"
                      >
                        {question}
                      </button>
                    ),
                  )}
                </div>
              )}

              <form
                onSubmit={handleSubmit}
                className="rounded-2xl border border-slate-700 bg-slate-900 p-2 shadow-xl shadow-black/20 focus-within:border-emerald-500/70"
              >
                <textarea
                  value={input}
                  onChange={(event) => {
                    setInput(event.target.value);
                  }}
                  onKeyDown={handleKeyDown}
                  disabled={busy}
                  rows={3}
                  maxLength={2000}
                  placeholder="Ask a question about nutrition..."
                  className="w-full resize-none bg-transparent px-3 py-2 text-sm leading-6 text-slate-100 outline-none placeholder:text-slate-500 disabled:cursor-not-allowed sm:text-base"
                />

                <div className="flex items-center justify-between gap-4 px-2 pb-1">
                  <span className="text-xs text-slate-500">
                    Enter to send · Shift + Enter for a new line
                  </span>

                  <button
                    type="submit"
                    disabled={
                      busy || !input.trim()
                    }
                    className="rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
                  >
                    {busy ? "Working..." : "Send"}
                  </button>
                </div>
              </form>

              <p className="mt-3 text-center text-xs text-slate-600">
                Answers are generated only from the retrieved
                nutrition textbook context.
              </p>
            </div>
          </section>

          <aside className="border-t border-slate-800 bg-slate-900/50 p-5 lg:border-t-0 lg:p-6">
            <div className="sticky top-6">
              <div className="mb-5">
                <h2 className="text-base font-semibold">
                  Retrieved sources
                </h2>

                <p className="mt-1 text-sm leading-6 text-slate-400">
                  These passages were retrieved from Supabase
                  and supplied to Gemini.
                </p>
              </div>

              {sources.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-700 p-6 text-center">
                  <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-slate-800 text-lg">
                    📄
                  </div>

                  <p className="text-sm text-slate-400">
                    Ask a question to view the matching textbook
                    passages and page numbers.
                  </p>
                </div>
              ) : (
                <div className="max-h-[calc(100vh-180px)] space-y-3 overflow-y-auto pr-1">
                  {sources.map((source) => {
                    const similarity =
                      typeof source.similarity ===
                      "number"
                        ? source.similarity.toFixed(3)
                        : "N/A";

                    return (
                      <article
                        key={`${source.number}-${source.page}-${source.similarity}`}
                        className="rounded-2xl border border-slate-800 bg-slate-950 p-4"
                      >
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <span className="rounded-lg bg-emerald-500/15 px-2.5 py-1 text-xs font-semibold text-emerald-300">
                            Source [{source.number}]
                          </span>

                          <span className="text-xs text-slate-500">
                            Score {similarity}
                          </span>
                        </div>

                        <p className="mb-2 text-sm font-medium text-slate-200">
                          Page{" "}
                          {source.page ?? "Unknown"}
                        </p>

                        <p className="line-clamp-6 text-sm leading-6 text-slate-400">
                          {source.content}
                        </p>

                        <p className="mt-3 truncate border-t border-slate-800 pt-3 text-xs text-slate-600">
                          {source.source}
                        </p>
                      </article>
                    );
                  })}
                </div>
              )}
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}