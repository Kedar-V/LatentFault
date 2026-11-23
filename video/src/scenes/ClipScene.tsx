import React from "react";
import { AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { C, mono, sans } from "../theme";
import { Count, Rise } from "../parts";

type Stat = { at: number; k: number; n: number; text: string; color?: string };
type Answer = { at: number; until?: number; title: string; lines: string[]; color?: string };

type Props = {
  clip: string;
  tag: string;
  caption: string;
  stat: Stat;
  answers: Answer[];
  tagColor?: string;
};

// A recorded demo run, zoomed onto the 3D view, with a label, a caption, the model's recorded answer
// (typed out at the moment it appears in the run) and a stat that lands at the outcome.
export const ClipScene: React.FC<Props> = ({ clip, tag, caption, stat, answers, tagColor = C.teal }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", fontFamily: sans }}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <ZoomedVideo src={staticFile(`clips/${clip}.mp4`)} trimBefore={Math.round(0.3 * fps)} />
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 70, top: 60 }}>
        <Rise at={0.2}>
          <div style={{ background: tagColor, color: "#04111F", fontWeight: 800, fontSize: 34, padding: "12px 26px", borderRadius: 999, letterSpacing: "0.02em" }}>{tag}</div>
        </Rise>
      </div>
      {answers.map((a) => <AnswerCard key={a.title} {...a} />)}
      <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 46 }}>
        <Rise at={0.5}>
          <div style={{ background: "rgba(4,12,24,0.85)", color: "#fff", fontSize: 46, fontWeight: 700, padding: "18px 40px", borderRadius: 22, maxWidth: 1500, textAlign: "center" }}>
            {caption}
          </div>
        </Rise>
      </AbsoluteFill>
      <StatCard {...stat} />
    </AbsoluteFill>
  );
};

const ZoomedVideo: React.FC<{ src: string; trimBefore: number }> = ({ src, trimBefore }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <Video
      src={src}
      trimBefore={trimBefore}
      muted
      style={{
        width: 1920,
        height: 1080,
        transformOrigin: "50% 45%",
        scale: interpolate(frame, [0, durationInFrames], [1, 1.05], { extrapolateRight: "clamp" }),
      }}
    />
  );
};

// The model's recorded answer, typed out in a terminal card on the left.
const AnswerCard: React.FC<Answer> = ({ at, until, title, lines, color = C.teal }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const text = lines.join("\n");
  const chars = Math.floor(interpolate(frame, [at * fps, at * fps + 1.4 * fps], [0, text.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  if (frame < at * fps || (until !== undefined && frame >= until * fps)) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 70,
        top: 150,
        width: 940,
        background: "rgba(4,12,24,0.92)",
        border: `3px solid ${color}`,
        borderRadius: 22,
        padding: "22px 28px",
        opacity: interpolate(frame, [at * fps, at * fps + 0.25 * fps], [0, 1], { extrapolateRight: "clamp" }),
      }}
    >
      <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: "0.14em", color, textTransform: "uppercase", fontFamily: sans }}>{title}</div>
      <div style={{ fontFamily: mono, fontSize: 30, lineHeight: 1.4, color: "#fff", whiteSpace: "pre-wrap", marginTop: 10 }}>{text.slice(0, chars)}</div>
    </div>
  );
};

const StatCard: React.FC<Stat> = ({ at, k, n, text, color = C.coral }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = interpolate(frame, [at * fps, at * fps + 0.5 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  return (
    <div
      style={{
        position: "absolute",
        right: 70,
        top: 150,
        width: 520,
        padding: "28px 34px",
        borderRadius: 28,
        background: "rgba(4,12,24,0.92)",
        border: `3px solid ${color}`,
        opacity: enter,
        translate: `${(1 - enter) * 80}px 0px`,
        color: C.ink,
      }}
    >
      <Count k={k} n={n} at={at + 0.2} color={color} size={120} />
      <div style={{ fontSize: 32, fontWeight: 600, lineHeight: 1.3, marginTop: 8 }}>{text}</div>
    </div>
  );
};
