# Teaching style guide (v0.5)

Use with `TERMINOLOGY.md` for gold answers and inference.

## Voice

- Sound like Ei Maung / Saturngod books: complete sentences, direct teaching.
- Prefer **book sentences** over repeated template openers (`ကျွန်တော်တို့ လက်တွေ့…`, `ဥပမာ ပြောရရင်…`) unless the book already uses them.
- No dictionary calques (`…ခြင်း` chains for English `-ing`).

## Code explanation

- Say what **this** function or snippet does first.
- Name identifiers from the code (`get_odd_numbers`, `odd_numbers`, `range`, `append`) where relevant.
- Use glossary terms: **မ ဂဏန်း** (odd), **စုံ ဂဏန်း** (even), **စာရင်း** (list), not **တစ်တန်း** unless you mean **layout columns**.

## Structure

- Up to three short paragraphs: definition → how it works → example or result.
- End on a full sentence with `။`.
- Keep English keywords inside code; explain in Myanmar around them.

## Inference guide

When `TUTOR_STYLE_GUIDE=true`, the app and SFT chat export append the text in [`inference_prompt.md`](inference_prompt.md) (`## general`, plus `## with_code` when a code block is present). Edit that file as the single source of truth; do not duplicate hints here.
