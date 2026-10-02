import { useState } from "react";
const failureEmojis = [
  "💥", "😵‍💫", "🧨", "😿", "🥀", "🫠", "🧟", "🫤"
];

export default function FailureEmoji() {
  // picked once, so that it does not change when the component re-renders.
  const [randomEmoji] = useState(() => failureEmojis[Math.floor(Math.random() * failureEmojis.length)]);

  return (
    <span role="img" aria-label="failure">
      {randomEmoji}
    </span>
  );
}
