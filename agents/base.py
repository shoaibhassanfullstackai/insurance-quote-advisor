from utils.llm import load_prompt


class BaseAgent:
    prompt_file: str = ""

    @property
    def system_prompt(self) -> str:
        return load_prompt(self.prompt_file)
