import { type LLMProvider } from "@/components/LLMProviders";

import "./styles.css";

interface LLMProviderSelectorProps {
  providersJson: LLMProvider[];
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}

function LLMProviderSelector({
  value,
  onChange,
  providersJson,
}: LLMProviderSelectorProps) {

  return (
    <select
      className="form-select form-select-sm"
      style={{ width: "220px" }}
      value={value}
      onChange={onChange}
    >
      {providersJson.length === 0 && (
        <option value="">No providers available</option>
      )}
      {providersJson.map((provider) => (
        <option key={provider.id} value={String(provider.id)}>
          {provider.name}
        </option>
      ))}
    </select>
  );
}

export default LLMProviderSelector;
