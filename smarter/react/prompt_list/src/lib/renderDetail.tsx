export const renderDetailRow = (
  label: string,
  value: string | number | null | undefined,
) => {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  return (
    <tr>
      <td className="prompt-list-detail-label">{label}</td>
      <td className="prompt-list-detail-value">{value}</td>
    </tr>
  );
};
