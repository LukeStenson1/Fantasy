import { useEffect } from "react";

/**
 * Google AdSense ad unit component.
 * Usage: <AdUnit slot="XXXXXXXXXX" format="auto" />
 * Formats: "auto", "horizontal", "vertical", "rectangle"
 */
export default function AdUnit({ slot, format = "auto", className = "" }) {
  useEffect(() => {
    try {
      if (window.adsbygoogle) {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
      }
    } catch (e) {
      console.error("AdSense error:", e);
    }
  }, []);

  return (
    <div className={`ad-unit overflow-hidden ${className}`}>
      <ins
        className="adsbygoogle"
        style={{ display: "block" }}
        data-ad-client="ca-pub-3121309985749965"
        data-ad-slot={slot}
        data-ad-format={format}
        data-full-width-responsive="true"
      />
    </div>
  );
}
