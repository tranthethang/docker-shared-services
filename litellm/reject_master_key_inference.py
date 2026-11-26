"""Reject model calls that authenticate with the proxy master key."""

from fastapi import HTTPException
from litellm.constants import LITELLM_PROXY_MASTER_KEY_ALIAS
from litellm.integrations.custom_logger import CustomLogger


class RejectMasterKeyInference(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if getattr(user_api_key_dict, "api_key", None) == LITELLM_PROXY_MASTER_KEY_ALIAS:
            raise HTTPException(
                status_code=401,
                detail="The master key cannot call model APIs. Use a virtual key.",
            )


handler = RejectMasterKeyInference()
