from __future__ import annotations

import os


# ---------------------------------------------------------------
# TEST ENVIRONMENT SAFETY
# ---------------------------------------------------------------
#
# Prevent the normal pytest suite from making real OpenAI API
# requests.
#
# Individual tests that need to simulate an enabled LLM can still
# monkeypatch the configuration and OpenAI client explicitly.
#
# Setting the variable before application modules are imported also
# prevents load_dotenv() from replacing it with the real key from
# the project's .env file.
# ---------------------------------------------------------------

os.environ["OPENAI_API_KEY"] = ""
