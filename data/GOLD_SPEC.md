# Gold Sample Specification (v0.5)

Every processed sample must pass this spec. Extraction leftovers are not gold.

Answers should sound like a person teaching (Ei Maung / Saturngod book voice), not a dictionary. **v0.5:** catalog gold in `scripts/gold_samples/` is canonical. Book sentences from `data/raw/*_candidates.jsonl` may be prepended only when they match the question; they must never replace the catalog answer. Follow [`TERMINOLOGY.md`](TERMINOLOGY.md) and [`STYLE_GUIDE.md`](STYLE_GUIDE.md). Do not use calques such as `ဒြပ်စင်များ ခြုံခြင်း`. Keep English API words (React, Fragment, `useState`, Python) as the books do.

## Instruction

- One clear student question a learner would type
- Includes: `မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ`
- Not a chopped book paragraph + `ဆိုတာ ဘာလဲ?`
- Not an exercise title (`လေ့ကျင့်ခန်း`)
- Not truncated mid-word

## Input

- `concept_qa`: empty string
- `explain_code`: complete, valid code that the output explains
- `debug_explain`: intentionally broken code; output must show a real fix

## Output (3-part teaching structure)

1. One-sentence definition or what the code does
2. Step-by-step explanation (2–6 short paragraphs)
3. One concrete example or expected result

Must:

- End on a complete sentence (normally `။`)
- Follow `TERMINOLOGY.md`
- Describe **this** input code (no mismatch)

Must not:

- Refer to missing figures (`flowchart ကို ကြည့်ပါ`, `အထက်ပါ ပုံ`)
- Include multiple-choice leftovers (`A. B. C.`)
- Include Discord / Telegram / “this book” navigation
- End mid-sentence (`ပြီးလျှင်`, `ဆိုပြီး`)

## Debug

- Input = broken code
- Output = what is wrong + why + corrected code that actually fixes it
- Corrected code must differ from the broken input

## Gold example

```json
{
  "instruction": "Python မှာ user ဆီက နာမည် လက်ခံပြီး ပြန်ထုတ်ပြတဲ့ code ကို ရှင်းပြပါ။ မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ",
  "input": "username = input(\"What is your name ? : \")\nprint(\"Your name is \", username)",
  "output": "ဒီ code က user ဆီက နာမည် လက်ခံပြီး screen ပေါ်မှာ ပြန်ပြပါတယ်။\n\nပထမကြောင်းမှာ input() က မေးခွန်းကို ပြပြီး user ရိုက်ထည့်တဲ့ စာကို username variable ထဲ သိမ်းပါတယ်။\n\nဒုတိယကြောင်းမှာ print() က Your name is နဲ့အတူ သိမ်းထားတဲ့ နာမည်ကို ထုတ်ပြပါတယ်။\n\nဥပမာ user က Aung ရိုက်ရင် Your name is  Aung ထွက်ပါတယ်။"
}
```
