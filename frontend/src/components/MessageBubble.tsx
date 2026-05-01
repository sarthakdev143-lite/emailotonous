import type { MessageRecord } from "../types";

interface MessageBubbleProps {
  message: MessageRecord;
}

function formatTimestamp(timestamp: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const outbound = message.direction === "outbound";

  return (
    <article className={`flex ${outbound ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-[24px] border px-4 py-3 ${
          outbound
            ? "border-brand/20 bg-brand text-white"
            : "border-stroke bg-canvas text-ink"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-6">{message.body}</p>
        <div
          className={`mt-3 flex items-center justify-between gap-3 text-[0.72rem] ${
            outbound ? "text-white/75" : "text-mist"
          }`}
        >
          <span>{outbound ? "Agent" : "Prospect"}</span>
          <span>{formatTimestamp(message.timestamp)}</span>
        </div>
      </div>
    </article>
  );
}
