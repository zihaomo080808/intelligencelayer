# generator/cot_prompt.py
def build_prompt(profile, items):
    msgs = [
        {"role":"system","content":(
            "You’re an AI that recommends startup opportunities via first-principles CoT."
        )},
        {"role":"system","content":f"User stances: {profile['stances']}"},
    ]
    for i,item in enumerate(items,1):
        msgs.append({
            "role":"system",
            "content":f"Candidate {i}: {item['title']} — {item['description']} (URL: {item['url']})"
        })
    msgs.append({
        "role":"user","content":(
            "Pick top 3. For each, give:\n"
            "1) Why it matters (first principles)\n"
            "2) Next-step action\n"
            "Format as a text response with witty, morbidly hilarious commentary—just two friends laughing at the madness. Make sure it remains as casual as possible: (example but do not, look at syntax and casual wording but do not take example literally and employ in every response, only for reference: if you're not looking at this, its pure damnation.)"
        )
    })
    return msgs
