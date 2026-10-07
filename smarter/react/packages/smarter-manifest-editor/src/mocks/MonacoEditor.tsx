/**
 * A stand-in for @monaco-editor/react in tests. Monaco loads from a CDN at runtime, which jsdom
 * cannot do, so tests replace the editor with a textarea that has the same value and onChange.
 */
type EditorProps = { value?: string; onChange?: (value: string | undefined) => void };

export default function MonacoEditor({ value, onChange }: EditorProps) {
  return <textarea aria-label="Manifest YAML" value={value} onChange={(e) => onChange?.(e.target.value)} />;
}
