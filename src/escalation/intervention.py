"""Human intervention contract used by interactive replay."""

from typing import Callable, Optional


class HumanIntervention:
    """Pauses replay until an operator confirms the UI is ready to continue."""

    def __init__(self, input_reader: Optional[Callable[[str], str]] = None):
        self.input_reader = input_reader or input

    async def wait_for_operator(self, action_required: str) -> None:
        """Display the required action and wait for the operator to continue."""
        prompt = (
            "\n--- HUMAN INTERVENTION REQUIRED ---\n"
            f"{action_required}\n"
            "Perform the action in the browser, then press Enter here to resume: "
        )
        await __import__("asyncio").to_thread(self.input_reader, prompt)
