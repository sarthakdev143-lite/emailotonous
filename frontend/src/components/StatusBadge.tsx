interface StatusBadgeProps {
  label: string;
}

const STATUS_CLASSES: Record<string, string> = {
  pending: "bg-mist/10 text-mist",
  outreach_sent: "bg-brandSoft text-brand",
  negotiating: "bg-gold/15 text-gold",
  slot_proposed: "bg-rose/55 text-ink",
  booked: "bg-brand text-white",
  closed_no_fit: "bg-ink/10 text-ink",
  closed_no_reply: "bg-stroke text-mist",
};

export default function StatusBadge({ label }: StatusBadgeProps) {
  const className = STATUS_CLASSES[label] ?? "bg-stroke text-ink";

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-[0.72rem] font-semibold uppercase tracking-[0.14em] ${className}`}
    >
      {label.replaceAll("_", " ")}
    </span>
  );
}
