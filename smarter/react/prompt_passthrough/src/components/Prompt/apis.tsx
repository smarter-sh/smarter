

export default function getApiUrl(llmProviderId: string) {
    switch (llmProviderId) {
      case "1":
        return "https://api.openai.com/v1";
      case "2":
        return "https://api.anthropic.com/v1";
      case "3":
        return "https://api.google.com/v1";
      default:
        return "https://api.openai.com/v1";
    }
}
