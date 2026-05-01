import type { ReactNode } from "react";

import type { ThreadDetail as ThreadDetailRecord } from "../types";
import MessageBubble from "./MessageBubble";
import StatusBadge from "./StatusBadge";

interface ThreadDetailProps {
  thread: ThreadDetailRecord | null;
  loading: boolean;
  error: string | null;
  onTriggerThread: () => Promise<void>;
  triggerDisabled: boolean;
  triggerLabel: string;
  triggerLoading: boolean;
  fallbackPanel: ReactNode;
}

function formatSlot(slot: string): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(slot));
}

export default function ThreadDetail({
  thread,
  loading,
  error,
  onTriggerThread,
  triggerDisabled,
  triggerLabel,
  triggerLoading,
  fallbackPanel,
}: ThreadDetailProps) {
  if (loading) {
    return <section className="panel-frame flex min-h-[32rem] items-center justify-center p-8 text-sm text-mist">Loading thread...</section>;
  }

  if (error) {
    return <section className="panel-frame min-h-[32rem] p-8 text-sm text-ink">{error}</section>;
  }

  if (thread === null) {
    return (
      <section className="panel-frame soft-grid flex min-h-[32rem] items-center justify-center p-8 text-center text-sm text-mist">
        Pick a thread to inspect the conversation, then trigger the next move from here.
      </section>
    );
  }

  return (
    <section className="panel-frame flex min-h-[32rem] flex-col overflow-hidden">
      <header className="border-b border-stroke px-6 py-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="section-title text-[1.9rem]">
                {thread.prospect_name ?? thread.prospect_email}
              </h2>
              <StatusBadge label={thread.status} />
            </div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">{thread.config.gig_description}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {thread.bookings.map((booking) => (
                <span
                  key={booking.id}
                  className="rounded-full border border-stroke bg-canvas px-3 py-1 text-xs uppercase tracking-[0.12em] text-mist"
                >
                  {booking.status}: {formatSlot(booking.slot)}
                </span>
              ))}
            </div>
          </div>
          <button
            type="button"
            disabled={triggerDisabled || triggerLoading}
            onClick={() => {
              void onTriggerThread();
            }}
            className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand disabled:cursor-not-allowed disabled:bg-stroke disabled:text-mist"
          >
            {triggerLoading ? "Working..." : triggerLabel}
          </button>
        </div>
      </header>

      <div className="grid flex-1 gap-6 p-6 xl:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="flex min-h-[20rem] flex-col gap-4 overflow-y-auto pr-2">
          {thread.messages.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-stroke p-6 text-sm text-mist">
              No messages yet. Trigger the agent to send the first outreach.
            </div>
          ) : (
            thread.messages.map((message) => <MessageBubble key={message.id} message={message} />)
          )}
        </div>

        <aside className="space-y-4">
          <div className="rounded-[24px] border border-stroke bg-canvas p-5">
            <p className="text-xs uppercase tracking-[0.18em] text-mist">Gig settings</p>
            <p className="mt-3 text-sm text-ink">
              Budget ceiling: <span className="font-semibold">${thread.config.budget_ceiling}</span>
            </p>
            <p className="mt-2 text-sm text-ink">Tone: {thread.config.tone}</p>
            <div className="mt-4 space-y-2">
              {thread.config.available_slots.map((slot) => (
                <div key={slot} className="rounded-2xl border border-stroke bg-panel px-3 py-2 text-xs text-mist">
                  {formatSlot(slot)}
                </div>
              ))}
            </div>
          </div>
          {fallbackPanel}
        </aside>
      </div>
    </section>
  );
}
