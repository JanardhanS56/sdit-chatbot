"""Extract the final clean card set from the issue note."""

import json
import re
from pathlib import Path


ISSUE_FILE = Path(r"D:\Obsidian Vault\D\Issue in DB.md")
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "manual_cards.json"


def main() -> None:
    markdown = ISSUE_FILE.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\s*(\[.*?\])\s*```", markdown, flags=re.DOTALL)
    if not blocks:
        raise ValueError("No JSON card block found in the issue note")

    cards = json.loads(blocks[-1])
    if not isinstance(cards, list) or not cards:
        raise ValueError("The final JSON block is not a non-empty card list")

    ids = [card.get("id") for card in cards]
    if any(not card_id for card_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Cards must have non-empty unique IDs")

    required = {"id", "category", "title", "content", "source"}
    for card in cards:
        missing = required - card.keys()
        if missing:
            raise ValueError(f"{card.get('id', '<unknown>')} missing: {sorted(missing)}")

    OUTPUT_FILE.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(cards)} clean cards to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()