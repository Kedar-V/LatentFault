import { Composition } from "remotion";
import { FADE, SCENES, Walkthrough } from "./Walkthrough";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Walkthrough"
      component={Walkthrough}
      durationInFrames={SCENES.reduce((a, s) => a + Math.round(s * 30), 0) - FADE * (SCENES.length - 1)}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
