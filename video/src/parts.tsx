import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, sans } from "./theme";

const ease = Easing.bezier(0.16, 1, 0.3, 1);

// Text that rises and fades in at `at` seconds into its scene.
export const Rise: React.FC<{ at?: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ at = 0, children, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div
      style={{
        opacity: interpolate(frame, [at * fps, at * fps + 0.6 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease }),
        translate: interpolate(frame, [at * fps, at * fps + 0.6 * fps], ["0px 40px", "0px 0px"], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease }),
        ...style,
      }}
    >
      {children}
    </div>
  );
};

// Full-frame dark backdrop with a soft glow, shared by the title and card scenes.
export const Backdrop: React.FC<{ children: React.ReactNode; glow?: string }> = ({ children, glow = C.coral }) => (
  <AbsoluteFill
    style={{
      backgroundColor: C.bg,
      backgroundImage: `radial-gradient(circle at 78% 18%, ${glow}33, transparent 45%), radial-gradient(circle at 12% 90%, ${C.teal}22, transparent 40%)`,
      fontFamily: sans,
      color: C.ink,
      padding: "120px 140px",
    }}
  >
    {children}
  </AbsoluteFill>
);

// Small uppercase label above a headline.
export const Kicker: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color = C.coral }) => (
  <div style={{ fontSize: 34, fontWeight: 800, letterSpacing: "0.18em", textTransform: "uppercase", color }}>{children}</div>
);

// A big counted number, e.g. "10 / 10", that ticks up from 0 starting at `at` seconds.
export const Count: React.FC<{ k: number; n: number; at: number; color?: string; size?: number }> = ({ k, n, at, color = C.coral, size = 150 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const shown = Math.round(interpolate(frame, [at * fps, at * fps + 0.8 * fps], [0, k], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease }));
  return (
    <span style={{ fontSize: size, fontWeight: 800, color, letterSpacing: "-0.03em", fontVariantNumeric: "tabular-nums" }}>
      {shown}
      <span style={{ fontSize: size * 0.45, color: C.muted }}> / {n}</span>
    </span>
  );
};
