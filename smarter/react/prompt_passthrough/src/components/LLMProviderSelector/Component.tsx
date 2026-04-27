
import './styles.css';

interface LLMProviderSelectorProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}

function LLMProviderSelector({ value, onChange }: LLMProviderSelectorProps) {

  return (
    <select
      className="form-select form-select-sm"
      style={{ width: "220px" }}
      value={value}
      onChange={onChange}
    >
      <option value="1">OpenAI</option>
      <option value="2">Anthropic</option>
      <option value="3">Google Gemini</option>
    </select>
  );
}

export default LLMProviderSelector;
