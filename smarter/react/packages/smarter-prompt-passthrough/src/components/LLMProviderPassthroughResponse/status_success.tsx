import { useEffect, useState } from "react";
import "./styles.css";



const successEmojis = [
  "🎉", "🥳", "🚀", "🌟", "🏆", "🥇", "🎊", "🍾", "😸", "💯",
  "🤩", "🥂", "🎈", "🦄", "🕺", "💃", "🤗", "🥰", "😻", "👑", "🧁", "🍀", "🥒"
];

export default function SuccessEmoji() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShow(true), 250);
    return () => clearTimeout(timer);
  }, []);

  // picked once, so that it does not change when `show` re-renders the component.
  const [randomEmoji] = useState(() => successEmojis[Math.floor(Math.random() * successEmojis.length)]);

  return (
    <span
      role="img"
      aria-label="success"
      className={`emoji-animate${show ? " emoji-animate--show" : ""}`}
    >
      {randomEmoji}
    </span>
  );
}
