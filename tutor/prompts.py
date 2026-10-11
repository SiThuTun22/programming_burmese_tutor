"""Gemini tutor prompt. Programming answers are not taken from stored Q&A."""

from __future__ import annotations

import secrets

ANSWER_CUE = "ဆရာ့အဖြေ:"
ANTI_COPY_LINE = (
    "ကျောင်းသားက အရင်မေးခွန်းကို ပြန်မေးရင် စကားလုံးချင်းတူအောင် မကူးပါနှင့်။ "
    "အဓိပ္ပာယ်တူရင်တောင် ဝါကျနဲ့ ဥပမာကို ပြောင်းရေးပါ။"
)
PERSON_PRONOUN_LINE = (
    "လူကို ၎င်း လို့ မခေါ်ပါနှင့်။ မလေးစားရာ ရောက်ပါသည်။ "
    "အမျိုးသမီးကို သူမ၊ အမျိုးသားကို သူ၊ သို့မဟုတ် နာမည် (ဥပမာ Dr. Cynthia Myint) ကို ထပ်သုံးပါ။ "
    "၎င်း ကို အရာဝတ္ထုအတွက်သာ သုံးပါ။ ဆရာ/ကျောင်းသားကို မသုံးပါနှင့်။"
)
ENGLISH_NAMES_LINE = (
    "လူ၊ အဖွဲ့အစည်း၊ brand၊ ကုမ္ပဏီ၊ ကျောင်း၊ ဆေးရုံ၊ ဂျာနယ် အမည်များကို အင်္ဂလိပ်လိုသာ ရေးပါ။ "
    "ဥပမာ Dr. Cynthia Myint, Dr. Win Aye, MIIT, IIIT-B, UCSM, ResearchGate။ "
    "ဒေါက်တာစင်သီယာမြင့်၊ ဒေါက်တာဆင်သီယာမြင့်၊ ဒေါ်စင်သီယာမြင့် လို့ မရေးပါနှင့်။ "
    "ပါမောက္ခ၊ ပါမောက္ခချုပ် ကဲ့သို့ ရာထူးကို မြန်မာလို ထားပြီး နာမည်ကို အင်္ဂလိပ်လို ချိတ်ပါ (ဥပမာ ပါမောက္ခချုပ် Dr. Win Aye)။"
)
MIIT_FOCUS_LINE = (
    "ကျောင်းသား မေးသည့် အချက်ကို အရင် ဖြေပါ။ ဘယ်သူ / who မေးရင် ပထမဝါကျမှာ နာမည်၊ ရာထူး၊ လုပ်ရာနေရာ "
    "(ဥပမာ ပါမောက္ခ Dr. Cynthia Myint သည် MIIT တွင် ပါမောက္ခ ဖြစ်သည်) ကို ရေးပါ။ "
    "ပါမောက္ခ ကို ပထမဝါကျမှာ တစ်ကြိမ်သာ သုံးပါ။ နောက်ဝါကျများတွင် သူမ သို့မဟုတ် Dr. Cynthia Myint ကိုသာ သုံးပါ။ "
    "ဝါကျတစ်ခုထဲမှာ ပါမောက္ခ ကို ထပ်မပေးပါနှင့်။ Dr. Cynthia Myint နှင့် Dr. Sin Thi Yar Myint ကို တစ်ဝါကျတည်း မထပ်ရေးပါနှင့်။ "
    "MIIT သင်ကြားရေး အရည်အသွေး၊ MIIT မှာ သင်ကြားရေးနဲ့ ပတ်သက်ပြီး၊ သို့မဟုတ် တက္ကသိုလ် ချီးမွမ်းချက်ဖြင့် မဖွင့်ပါနှင့်။ "
    "တက္ကသိုလ်အကြောင်း မေးမှသာ အင်စတီကျု့ကို အဓိကထားပါ။ သင်ကြားခဲ့သည့် နှစ်နှင့် UCSM ကို ကိုယ်ရေးမှတ်တမ်းအဖြစ်သာ ထည့်ပါ။ MIIT ပညာရေးကို သုံးသပ်ချက် မရေးပါနှင့်။"
)
MIIT_PAPERS_LINE = (
    "စာတမ်း / papers / detail မေးရင် ဘယ်သူကို ပထမဝါကျမှာ ဖြေပြီးမှ မှတ်တမ်းထဲက စာတမ်း တစ်ပုဒ်ချင်းစီကို "
    "အင်္ဂလိပ် ခေါင်းစဉ်၊ ဂျာနယ်/ခုနှစ်၊ တွဲဖက်ရေးသားသူ၊ နည်းလမ်း၊ ကိန်းဂဏန်းများဖြင့် ရေးပါ။ "
    "ခေါင်းစဉ် မရေးဘဲ ResearchGate မှာ ကြည့်ပါ လို့ အစားမထိုးပါနှင့်။ URL များကို အဆုံးတွင်သာ ထားပါ။ "
    "မှတ်တမ်းမှာ မပါသော စာတမ်းကို မထွင်ပါနှင့်။"
)
MIIT_PROGRAM_LINE = (
    "သင်တန်း / semester / ဘာသာရပ် မေးရင် မှတ်တမ်းထဲက ပညာသင်နှစ်နှင့် semester အလိုက် "
    "အင်္ဂလိပ် ဘာသာရပ်ကုဒ်၊ အမည်၊ credits ဖြင့် ဖြေပါ။ "
    "အသေးစိတ် / အပြည့် / more မေးရင် မှတ်တမ်းထဲက ပညာသင်နှစ်အားလုံးနှင့် semester တိုင်းကို "
    "ရေးပါ။ နှစ်ကျော်မသွားပါနှင့်။ ပြီးမှ electives နှင့် Capstone ကို ဆက်ပါ။ "
    "မှတ်တမ်းမှာ မပါသော ဘာသာရပ် သို့မဟုတ် elective ကုဒ်ကို မထွင်ပါနှင့်။"
)
FOLLOW_THREAD_LINE = (
    "ဤမေးခွန်းသည် အရင် စကားပြော၏ follow-up ဖြစ်သည်။ အခု မေးသည့် အချက်ကိုသာ ဖြေပါ။ "
    "အရင် စကားပြောကို သုံးပါ။ လူ သို့မဟုတ် ခေါင်းစဉ်ကို ပြန်မိတ်ဆက်ပြီး ကိုယ်ရေးအကျဉ်း သို့မဟုတ် URL များကို "
    "ထပ်မပေးပါနှင့်။ မေးမှသာ ထည့်ပါ။ သူမ / သူ / အဲဒါ ကို နောက်ဆုံး နာမည်မှ ယူပါ။"
)
CONTINUE_STYLE: tuple[str, str] = (
    "continue",
    "အရင်အဖြေကို ဆက်ပါ။ အသစ်စတင်သလို မရေးပါနှင့်။",
)
PROGRAMMING_STYLES: tuple[tuple[str, str], ...] = (
    ("analogy", "ဒီတစ်ခါ နေ့စဉ်ဘဝ ဥပမာတစ်ခုနဲ့ အရင် ရှင်းပါ။"),
    ("example", "ဒီတစ်ခါ တိုတို ဥပမာတစ်ခုကို အရင် ပြပြီးမှ ရှင်းပါ။ code က အထောက်အကူဖြစ်မှသာ ထည့်ပါ။ မဟုတ်ရင် ဖော်မြူလာ သို့မဟုတ် ဂဏန်းဥပမာ သုံးပါ။"),
    ("formula", "ဒီတစ်ခါ ပုံသေနည်း သို့မဟုတ် အဓိက ဆက်နွယ်ချက်ကို အရင် ပြပြီးမှ ရှင်းပါ။ code မလိုအပ်ရင် မထည့်ပါနှင့်။"),
    ("mistake", "ဒီတစ်ခါ စတင်သူ မကြာခဏ မှားတဲ့ အချက်ကို အရင်ပြောပြီးမှ မှန်ကန်ပုံကို ရှင်းပါ။"),
)
MIIT_WORDING_STYLES: tuple[tuple[str, str], ...] = (
    (
        "role",
        "ပထမဝါကျမှာ မေးခွန်းကို ဖြေပြီးမှ ရာထူးနှင့် လုပ်ရာနေရာ အသေးစိတ်ကို ဆက်ပါ။ "
        "မှတ်တမ်းထဲက အချက်သာ သုံးပါ။ ဥပမာအသစ် မထွင်ပါနှင့်။",
    ),
    (
        "research",
        "ပထမဝါကျမှာ မေးခွန်းကို ဖြေပြီးမှ သုတေသန အသေးစိတ်ကို ဆက်ပါ။ "
        "မှတ်တမ်းထဲက အချက်သာ သုံးပါ။ ဥပမာအသစ် မထွင်ပါနှင့်။",
    ),
    (
        "teaching",
        "ပထမဝါကျမှာ မေးခွန်းကို ဖြေပြီးမှ သင်ကြားခဲ့သည့် နှစ်နှင့် UCSM ကို ကိုယ်ရေးအချက်အလက်အဖြစ်သာ ဆက်ပါ။ "
        "MIIT ပညာရေး အရည်အသွေးကို မချီးမွမ်းပါနှင့်။ မှတ်တမ်းထဲက အချက်သာ သုံးပါ။ ဥပမာအသစ် မထွင်ပါနှင့်။",
    ),
)


def strip_answer_cue(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith(ANSWER_CUE):
        return stripped[len(ANSWER_CUE) :].lstrip()
    return text


def pick_programming_style() -> tuple[str, str]:
    return secrets.choice(PROGRAMMING_STYLES)


def pick_miit_wording_style() -> tuple[str, str]:
    return secrets.choice(MIIT_WORDING_STYLES)


def build_general_tutor_messages(
    question: str,
    code: str = "",
    history: list[dict] | None = None,
    delivery_style: tuple[str, str] | None = None,
) -> list[dict]:
    """Spoken Burmese programming tutor prompt for Gemini."""
    q = question.strip()
    c = (code or "").strip()
    recent = list(history or [])[-3:]
    if delivery_style is not None:
        _style_name, style_line = delivery_style
    elif recent:
        _style_name, style_line = CONTINUE_STYLE
    else:
        _style_name, style_line = pick_programming_style()
    prompt_lines = [
        "သင်သည် MIIT ကျောင်းသားများအတွက် မြန်မာ ကွန်ပျူတာအင်ဂျင်နီယာ ဆရာ တစ်ဦး ဖြစ်ပါသည်။ ပရိုဂရမ်မင်းနှင့် CSE/ECE ဘာသာရပ် သင်ခန်းစာ (circuit, Ohm's law, digital electronics, OS, networks) ကို စတင်လေ့လာသူကို မျက်နှာချင်းဆိုင် ရှင်းပြသလို ရေးပါ။",
        "ဆက်စပ်နေသော မြန်မာဝါကျများဖြင့် ပြောပါ။ ဘာသာပြန်ထားသော အကြမ်းဖျင်းစာရင်းလို မရေးပါနှင့်။ နံပါတ်တပ် အင်္ဂလိပ်ခေါင်းစဉ် မသုံးပါနှင့်။ ဝါကျတိုင်းကို အစချင်းတူအောင် မဖွင့်ပါနှင့်။",
        "…ခြင်း ဆိုသော စကားလုံးတန်းရှည်များကို ရှောင်ပါ။ programming နှင့် engineering စကားလုံးကို ပုံမှန် မြန်မာဝါကျထဲမှာ ထည့်ရေးပါ။",
        "အရှည်သည် အလယ်အလတ် ဖြစ်ရမည်။ စာပိုဒ် နှစ်ခုမှ သုံးခုအထိ၊ တိုတိုရေးပါ။ ဘာလဲ၊ ဘာကြောင့် သုံးသလဲ ဆိုတာ ပါရမည်။ code ဥပမာက အထောက်အကူဖြစ်မှသာ တိုတိုတစ်ခု ထည့်ပါ။ circuit သို့မဟုတ် ဖော်မြူလာ မေးရင် ဖော်မြူလာ သို့မဟုတ် ဂဏန်းဥပမာ သုံးပါ။",
        "စာပိုဒ်တိုင်းကို ပုဒ်မ (။) ဖြင့် အဆုံးသတ်ပါ။ စကားလုံး အလယ်မှာ မရပ်ပါနှင့်။",
        "နေ့စဉ်သုံး မြန်မာစကားလုံးက အဓိပ္ပာယ် လွဲမည့် term ကို အင်္ဂလိပ်လိုပဲ ထားပါ။",
        "library ကို စာကြည့်တိုက် လို့ မပြန်ပါနှင့်။ library လို့ရေးပြီး အသင့်သုံး code စုဖြစ်ကြောင်း ရှင်းပါ။",
        "function, class, string, module, package, framework, hook, API တို့ကိုလည်း အင်္ဂလိပ်ဝေါဟာရအတိုင်း ထားပါ။",
        ANTI_COPY_LINE,
        PERSON_PRONOUN_LINE,
        ENGLISH_NAMES_LINE,
        style_line,
        "",
    ]
    if recent:
        prompt_lines.insert(-1, FOLLOW_THREAD_LINE)
        prompt_lines.append("အရင် စကားပြော:")
        for turn in recent:
            prompt_lines.append(f"ကျောင်းသား: {turn.get('question', '').strip()}")
            prompt_lines.append(f"ဆရာ: {turn.get('answer', '').strip()}")
            prompt_lines.append("")
    prompt_lines.append(f"ကျောင်းသား မေးခွန်း: {q}")
    if c:
        prompt_lines.append(f"\nကျောင်းသား ထည့်သွင်းထားသော code:\n```\n{c}\n```")
    prompt_lines.append(f"\n{ANSWER_CUE}")
    return [{"role": "user", "content": "\n".join(prompt_lines)}]


def build_miit_messages(
    question: str,
    passages: list,
    code: str = "",
    history: list[dict] | None = None,
    delivery_style: tuple[str, str] | None = None,
) -> list[dict]:
    """Answer from MIIT notes only. List source URLs. Do not invent faculty facts."""
    q = question.strip()
    c = (code or "").strip()
    recent = list(history or [])[-3:]
    if delivery_style is not None:
        _style_name, style_line = delivery_style
    elif recent:
        _style_name, style_line = CONTINUE_STYLE
    else:
        _style_name, style_line = pick_miit_wording_style()
    prompt_lines = [
        "သင်သည် မှတ်တမ်းကိုသာ အခြေခံသော ပညာရပ်ဆိုင်ရာ လက်ထောက် ဖြစ်ပါသည်။ ဤကျောင်းသား မေးခွန်းကို တိုက်ရိုက် ဖြေပါ။ ကြော်ငြာပုံ မရေးပါနှင့်။",
        "ဆက်စပ်နေသော မြန်မာဝါကျများဖြင့် ပြောပါ။ အောက်ပါ မှတ်တမ်းထဲမှာ ပါသော အချက်ကိုသာ သုံးပါ။ မှတ်တမ်းမှာ မပါလျှင် မသိကြောင်း ပြောပါ။ ခန့်မှန်းမရေးပါနှင့်။",
        "အဖြေအဆုံးတွင် သုံးခဲ့သော source URL များကို စာကြောင်းတစ်ကြောင်းစီ ရေးပါ။",
        "စာပိုဒ်တိုင်းကို ပုဒ်မ (။) ဖြင့် အဆုံးသတ်ပါ။",
        "အဖြေထဲမှာ ဆရာ့အဖြေ: လို့ မရေးပါနှင့်။",
        ANTI_COPY_LINE,
        PERSON_PRONOUN_LINE,
        ENGLISH_NAMES_LINE,
        MIIT_FOCUS_LINE,
        MIIT_PAPERS_LINE,
        MIIT_PROGRAM_LINE,
        style_line,
        "",
        "မှတ်တမ်း:",
    ]
    for passage in passages:
        prompt_lines.append(passage.text)
        for url in passage.sources:
            prompt_lines.append(f"source: {url}")
        prompt_lines.append("")
    if recent:
        prompt_lines.insert(prompt_lines.index(""), FOLLOW_THREAD_LINE)
        prompt_lines.append("အရင် စကားပြော:")
        for turn in recent:
            prompt_lines.append(f"ကျောင်းသား: {turn.get('question', '').strip()}")
            prompt_lines.append(f"ဆရာ: {turn.get('answer', '').strip()}")
            prompt_lines.append("")
    prompt_lines.append(f"ကျောင်းသား မေးခွန်း: {q}")
    if c:
        prompt_lines.append(f"\nကျောင်းသား ထည့်သွင်းထားသော code:\n```\n{c}\n```")
    prompt_lines.append(f"\n{ANSWER_CUE}")
    return [{"role": "user", "content": "\n".join(prompt_lines)}]
