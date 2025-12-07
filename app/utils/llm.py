from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_BASE_URL

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)


async def run_gpt(prompt: str, model: str = "gpt-4o-mini"):
    """
    Unified GPT call wrapper for structure extractor.
    Works with new OpenAI SDK (client.chat.completions.create).
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert document analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.2
        )

        return response.choices[0].message.content

    except Exception as e:
        raise RuntimeError(f"LLM error: {str(e)}")
