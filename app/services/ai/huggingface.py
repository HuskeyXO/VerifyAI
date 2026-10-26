import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()


class HuggingFaceProvider:

    def __init__(self):
        self.token = os.getenv("HF_TOKEN")
        self.model = os.getenv("HF_MODEL")

        if not self.token:
            raise ValueError("HF_TOKEN is not set")

        if not self.model:
            raise ValueError("HF_MODEL is not set")

        self.client = InferenceClient(
            api_key=self.token
        )

    def generate(self, prompt: str):

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1
        )

        return response.choices[0].message.content
