

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


export function getSmarterApiUrlSlug(llmProviderId: string) {
    switch (llmProviderId) {
      case "1":
        return "openai";
      case "2":
        return "anthropic";
      case "3":
        return "googleai";
      default:
        return "openai";
    }
}
