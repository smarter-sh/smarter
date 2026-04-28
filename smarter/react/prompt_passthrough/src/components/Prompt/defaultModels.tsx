

export default function getDefaultModel(llmProviderId: string) {
    switch (llmProviderId) {
      case "1":
        return "gpt-4o-mini";
      case "2":
        return "default-anthropic-model";
      case "3":
        return "default-google-model";
      default:
        return "gpt-4o-mini";
    }
}
