
export const failure_style = {
  color: "red",
  marginLeft: "10px",
};

export default function FailureEmoji() {

  const failureEmojis = [
    "💥", "😵‍💫", "🧨", "😿", "🥀", "🫠", "🧟", "🫤"
  ];

  const randomEmoji = failureEmojis[Math.floor(Math.random() * failureEmojis.length)];

  return (
    <span role="img" aria-label="failure">
      {randomEmoji}
    </span>
  );
}
