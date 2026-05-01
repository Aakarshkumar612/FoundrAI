import { memo, useEffect, useRef } from "react";

const HLS_SRC = "https://stream.mux.com/9JXDljEVWYwWu01PUkAemafDugK89o01BR6zqJ3aS9u00A.m3u8";

export const VideoPlayer = memo(function VideoPlayer() {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = ref.current;
    if (!video) return;

    let cleanup: (() => void) | undefined;

    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Native HLS (Safari)
      video.src = HLS_SRC;
      video.play().catch(() => {});
    } else {
      // hls.js for Chrome / Firefox / Edge
      import("hls.js").then(({ default: Hls }) => {
        if (!Hls.isSupported()) return;
        const hls = new Hls({ enableWorker: true, lowLatencyMode: false });
        hls.loadSource(HLS_SRC);
        hls.attachMedia(video);
        hls.once(Hls.Events.MANIFEST_PARSED, () => video.play().catch(() => {}));
        cleanup = () => hls.destroy();
      });
    }

    return () => cleanup?.();
  }, []);

  return (
    <video
      ref={ref}
      muted
      loop
      playsInline
      autoPlay
      className="w-full h-full object-cover"
    />
  );
});
