import React, { useState } from "react";
import "./styles.css";

interface TemplateSelectorProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}

function TemplateSelector({ value, onChange }: TemplateSelectorProps) {

  const [selectedValue, setSelectedValue] = useState(value);
  return (
    <select
      className="form-select form-select-sm ms-auto"
      style={{ width: "220px" }}
      value={selectedValue}
      onChange={(e) => {
        setSelectedValue(e.target.value);
        onChange(e);
      }}
    >
      <option value="1">Hello World</option>
      <option value="2">Message Roles</option>
      <option value="3">Function Call</option>
    </select>
  );
}

export default TemplateSelector;
