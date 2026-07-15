import re

# ISO country code map from emoji to 2-letter ISO code
def get_iso_from_emoji(emoji):
    if len(emoji) != 2:
        return ""
    # Emojis are composed of regional indicator symbols
    return "".join(chr(ord(c) - 127397) for c in emoji).lower()

with open('c:/UI-UX/union-bank-wise-reskin/src/pages/Home.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

def replace_flag(match):
    emoji = match.group(1)
    iso_code = get_iso_from_emoji(emoji)
    if iso_code:
        # flag-icons expects class="fi fi-xx"
        return f'<span className="country-flag fi fi-{iso_code} fis"></span>'
    return match.group(0)

new_content = re.sub(r'<span className="country-flag">(.*?)</span>', replace_flag, content)

with open('c:/UI-UX/union-bank-wise-reskin/src/pages/Home.jsx', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Replaced emojis with flag-icons classes")
