from __future__ import annotations

from ibus_voice.config import ProviderConfig
from ibus_voice.providers.gemini import GeminiProvider
from ibus_voice.providers.openai import OpenAIProvider
from ibus_voice.types import ProviderFailure


def build_provider(config: ProviderConfig):
    name = config.name.lower()
    if name == "openai":
        return OpenAIProvider.from_config(config)
    if name == "gemini":
        return GeminiProvider.from_config(config)
    raise ProviderFailure(name, f"unsupported provider: {config.name}")
