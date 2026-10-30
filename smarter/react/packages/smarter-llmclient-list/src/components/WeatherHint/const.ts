/**
 * The Get Weather example LLMClient, which the welcome tour suggests trying first: its name, and the
 * onboarding target that marks its name in the list. See WEATHER_LLMCLIENT_NAME in
 * smarter/apps/dashboard/views/views/api/welcome.py, and llm-clients/llmclient-weather.yaml in
 * https://github.com/smarter-sh/example-manifests.
 */
export const WEATHER_LLMCLIENT_NAME = "weather";
export const WEATHER_TARGET = "llmclient-weather";

/** The onboarding target attribute of an LLMClient's name in the list: only the Get Weather LLMClient's has one. */
export function weatherTargetAttribute(name: string): { "data-smarter-onboarding"?: string } {
  return name === WEATHER_LLMCLIENT_NAME ? { "data-smarter-onboarding": WEATHER_TARGET } : {};
}
