import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { loadSpaceGrotesk } from "../lib/localFonts";

interface KineticWordsProps {
  /** Space-separated words. Each one springs in with a stagger and keeps floating. */
  words?: string;
  /** Small label above the words (the channel kicker, e.g. "DARK · IA"). */
  kicker?: string;
  color?: string;
  accentColor?: string;
  kickerColor?: string;
  backgroundColor?: string;
  fontSize?: number;
  /** Frames between word entrances. */
  stagger?: number;
  /** Word indexes (0-based) painted with accentColor. Default: every 3rd word. */
  accentEvery?: number;
  /** "editorial" (left column, rule + kicker) or "centered" (legacy). */
  layout?: "editorial" | "centered";
  /** Corner label shown bottom-right (e.g. the channel name). */
  signature?: string;
}

/**
 * Kinetic typography that never sits still:
 *  - entrance: each word springs up from below with a stagger (damping 12 — lively);
 *  - idle: every word floats on its own sine wave and breathes (scale pulse),
 *    so the card keeps moving for the whole scene, like the reference shorts.
 *
 * REDESIGN (2026-11-15): the card used to be a flat cream rectangle with a
 * 3%-tall kicker floating in the middle of a 1080x1056 frame and one isolated
 * headline — 80% dead space, and it asked for "Inter" which is not installed,
 * so the browser synthesised a weight-900 fallback (the "amador" look).
 * Now: the bundled Space Grotesk (no network, real weights), an editorial
 * left column with a rule, a kicker that reads as a label, a headline block
 * that scales to fit, and a designed surface (grid + glow) so the frame is
 * never empty.
 *
 * Authored for the clone factory's top band (yt-motion-remotion.mjs). 100% original
 * render — no footage from any reference channel.
 */
export const KineticWords: React.FC<KineticWordsProps> = ({
  words = "",
  kicker = "",
  color = "#111111",
  accentColor = "#FF6A00",
  kickerColor = "#FF8A3D",
  backgroundColor = "#F0E6D8",
  fontSize = 110,
  stagger = 7,
  accentEvery = 3,
  layout = "editorial",
  signature = "",
}) => {
  const frame = useCurrentFrame();
  const { fps, height, width } = useVideoConfig();
  const { fontFamily } = loadSpaceGrotesk(["400", "500", "700"]);

  const list = words.split(/\s+/).filter(Boolean);
  const kickerIn = spring({ frame, fps, config: { damping: 20 } });

  // Scale the headline so it never overflows: the more words, the smaller.
  // A fixed size that overflows the frame is the classic amateur tell.
  const PAD = layout === "editorial" ? 84 : 40;
  const usable = width - PAD * 2;
  const avgCharW = 0.56; // Space Grotesk bold, uppercase
  const longestRun = list.reduce(
    (acc, w) => Math.max(acc, w.length),
    1
  );
  const perLine = Math.max(1, Math.floor(usable / (longestRun * avgCharW * fontSize)));
  const lines = Math.ceil(list.length / perLine);
  const lineBox = fontSize * 0.98;
  const maxLinesThatFit = Math.max(1, Math.floor((height * 0.52) / lineBox));
  const fit = lines > maxLinesThatFit ? maxLinesThatFit / lines : 1;

  // Fill pass: with few words the block leaves the frame half empty, which is
  // what made the old card look amateur. Grow it (up to 1.45x) so the type
  // block actually occupies the band.
  const TARGET_LINES = 2.4;
  const grow = Math.min(1.45, Math.max(1, TARGET_LINES / Math.max(1, lines * fit)));

  const size = Math.round(fontSize * Math.max(0.42, Math.min(1.45, fit * grow)));

  const ink = color;
  const accent = accentColor;

  return (
    <AbsoluteFill
      style={{
        background: backgroundColor,
        justifyContent: "center",
        alignItems: "center",
        overflow: "hidden",
        fontFamily,
      }}
    >
      {/* --- designed surface: soft glow + fine grid, so the frame is never a
             flat empty rectangle ------------------------------------------ */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(120% 90% at 78% 8%, ${accent}22 0%, transparent 55%),
                       radial-gradient(90% 70% at 8% 100%, ${ink}0D 0%, transparent 60%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${ink}0A 1px, transparent 1px),
                            linear-gradient(90deg, ${ink}0A 1px, transparent 1px)`,
          backgroundSize: "54px 54px",
          opacity: 0.55,
        }}
      />
      {/* accent edge on the left — gives the band a spine instead of a void */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: 10,
          background: `linear-gradient(180deg, ${accent} 0%, ${accent}55 55%, transparent 100%)`,
        }}
      />

      {layout === "editorial" ? (
        <>
          {/* kicker: rule + label, top-left, readable as a label */}
          <div
            style={{
              position: "absolute",
              left: PAD,
              top: 74,
              display: "flex",
              alignItems: "center",
              gap: 16,
              opacity: Math.min(1, Math.max(0, kickerIn)),
              transform: `translateY(${(1 - kickerIn) * -14}px)`,
            }}
          >
            <div
              style={{
                width: 52,
                height: 7,
                borderRadius: 4,
                background: kickerColor,
              }}
            />
            <div
              style={{
                fontSize: Math.max(22, Math.round(size * 0.2)),
                fontWeight: 700,
                letterSpacing: 7,
                color: kickerColor,
                textTransform: "uppercase",
                whiteSpace: "nowrap",
              }}
            >
              {kicker}
            </div>
          </div>

          {/* signature: bottom-right, small, anchors the composition */}
          {signature ? (
            <div
              style={{
                position: "absolute",
                right: PAD,
                bottom: 54,
                fontSize: Math.max(18, Math.round(size * 0.16)),
                fontWeight: 500,
                letterSpacing: 5,
                color: `${ink}8C`,
                textTransform: "uppercase",
              }}
            >
              {signature}
            </div>
          ) : null}
        </>
      ) : null}

      {/* --- ghost line: the headline repeated huge and faint behind the real
             type block. Fills the band with intent instead of empty colour. */}
      {layout === "editorial" && list.length ? (
        <div
          style={{
            position: "absolute",
            left: PAD - 18,
            bottom: 96,
            fontSize: Math.round(size * 2.1),
            fontWeight: 700,
            letterSpacing: -0.03,
            lineHeight: 0.8,
            color: `${ink}07`,
            textTransform: "uppercase",
            whiteSpace: "nowrap",
            overflow: "hidden",
            maxWidth: usable + 36,
          }}
        >
          {list.join(" ")}
        </div>
      ) : null}

      {/* --- the words ------------------------------------------------------- */}
      <div
        style={{
          position: "relative",
          display: "flex",
          flexWrap: "wrap",
          gap: `${size * 0.2}px ${size * 0.22}px`,
          justifyContent: layout === "editorial" ? "flex-start" : "center",
          alignItems: "baseline",
          width: layout === "editorial" ? usable : "88%",
          marginLeft: layout === "editorial" ? PAD : 0,
          marginTop: layout === "editorial" ? height * 0.06 : 0,
          padding: "0 3%",
        }}
      >
        {list.map((w, i) => {
          const delay = i * stagger;
          const s = spring({
            frame: frame - delay,
            fps,
            config: { damping: 12, stiffness: 130 },
            durationInFrames: 26,
          });
          // Idle motion: alternating vertical drift + a soft breathing pulse.
          const floatY = Math.sin((frame - delay) / 19) * size * 0.05 * (i % 2 === 0 ? 1 : -1);
          const pulse = 1 + Math.sin(frame / 15 + i) * 0.03;
          const isAccent = accentEvery > 0 && i % accentEvery === accentEvery - 1;
          return (
            <span
              key={i}
              style={{
                opacity: Math.min(1, Math.max(0, s)),
                transform: `translateY(${(1 - s) * 46 + floatY}px) scale(${(0.86 + 0.14 * s) * pulse})`,
                fontSize: size,
                fontWeight: 700,
                letterSpacing: -0.015,
                color: isAccent ? accent : ink,
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                lineHeight: 0.98,
                textShadow: isAccent ? `0 6px 26px ${accent}38` : "none",
              }}
            >
              {w}
            </span>
          );
        })}
      </div>

      {/* --- rule under the headline block: closes the composition ------------ */}
      {layout === "editorial" && list.length ? (
        <div
          style={{
            position: "absolute",
            left: PAD,
            right: PAD,
            bottom: 118,
            height: 2,
            background: `linear-gradient(90deg, ${ink}26 0%, ${ink}08 70%, transparent 100%)`,
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};
