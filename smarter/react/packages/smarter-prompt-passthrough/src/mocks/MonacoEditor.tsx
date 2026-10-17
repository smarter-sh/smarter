/**
 * A stand-in for @monaco-editor/react in tests. Monaco loads from a CDN at runtime, which jsdom
 * cannot do, so tests replace the editor with a textarea that has the same value and onChange, and
 * the editor's ariaLabel and readOnly options.
 */
type EditorProps = {
  value?: string;
  onChange?: (value: string | undefined) => void;
  options?: { ariaLabel?: string; readOnly?: boolean };
};

export default function MonacoEditor({ value, onChange, options }: EditorProps) {
  return (
    <textarea
      aria-label={options?.ariaLabel ?? "Request JSON"}
      readOnly={options?.readOnly}
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
    />
  );
}
