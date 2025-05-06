# generator/generator.py
import openai
from config import settings
from .cot_prompt import build_prompt

openai.api_key = settings.OPENAI_API_KEY

def generate_recommendation(profile, items):
    msgs = build_prompt(profile, items)
    resp = openai.ChatCompletion.create(
        model=settings.GENERATOR_MODEL,
        messages=msgs,
        temperature=0.7,
        max_tokens=500
    )
    return resp.choices[0].message.content
