import React, { useState } from "react";
import { promptTemplates } from "@/components/Prompt/templates";
import "@/components/TemplateSelector/styles.css";

interface TemplateSelectorProps {
  value: number;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}

function TemplateSelector({ value, onChange }: TemplateSelectorProps) {
  const [selectedValue, setSelectedValue] = useState(value);
  return (
    <select
      aria-label="Prompt template"
      className="form-select form-select-sm ms-auto"
      style={{ width: "220px" }}
      value={selectedValue}
      onChange={(e) => {
        const newValue = parseInt(e.target.value, 10);
        setSelectedValue(newValue);
        onChange(e);
      }}
    >
      {promptTemplates.map((t) => (
        <option key={t.id} value={t.id}>
          {t.name}
        </option>
      ))}
    </select>
  );
}

export default TemplateSelector;
