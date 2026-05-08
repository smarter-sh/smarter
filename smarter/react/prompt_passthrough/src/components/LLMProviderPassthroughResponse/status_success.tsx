import { useEffect, useState } from "react";
import "./styles.css";


export const success_style = {
  color: "green",
  marginLeft: "10px",
};

export default function SuccessEmoji() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShow(true), 250);
    return () => clearTimeout(timer);
  }, []);

  const successEmojis = [
    "🎉", "🥳", "🚀", "🌟", "🏆", "🥇", "🎊", "🍾", "😸", "💯",
    "🤩", "🥂", "🎈", "🦄", "🕺", "💃", "🤗", "🥰", "😻", "👑", "🧁", "🍀", "🥒"
  ];

  const randomEmoji = successEmojis[Math.floor(Math.random() * successEmojis.length)];

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
