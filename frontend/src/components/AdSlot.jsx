/**
 * Reusable ad slot. Currently renders a placeholder. Wire to AdSense / Carbon / etc later
 * by injecting the script into <head> and replacing this body with `<ins class='adsbygoogle'>`.
 *
 * Usage: <AdSlot slot="home-top" size="responsive" />
 */
export default function AdSlot({ slot = "default", size = "responsive", className = "" }) {
  return (
    <div
      className={`bg-slate-900/40 border border-dashed border-slate-800 rounded-md p-4 text-center ${className}`}
      data-ad-slot={slot}
      data-ad-size={size}
      data-testid={`ad-slot-${slot}`}
    >
      <div className="text-[9px] font-bold tracking-[0.25em] uppercase text-slate-600">Ad Slot · {slot}</div>
      <div className="text-xs text-slate-500 mt-1">Reserved for future ad placement</div>
    </div>
  );
}
