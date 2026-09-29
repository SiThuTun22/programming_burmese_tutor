"""Post-trim for repeated tutor paragraphs."""

from tutor.decode import collapse_repeated_paragraphs

LOOP = """Python ဆိုတာကတော့ programming language တစ်ခုဖြစ်ပါတယ်။

Python ဆိုတာ computer ကို ခိုင်းစေတဲ့ စကားဝှက် ဖြစ်ပါတယ်။

Python ဆိုတာ programming language တစ်ခု ဖြစ်ပါတယ်။

Python ဆိုတာ computer ကို ခိုင်းစေတဲ့ စကားဝှက် ဖြစ်ပါတယ်။

Python ဆိုတာ programming language တစ်ခု ဖြစ်ပါတယ်။

Python
"""


def test_collapses_python_stutter() -> None:
    out = collapse_repeated_paragraphs(LOOP)
    paras = [p for p in out.split("\n\n") if p.strip()]
    assert 1 <= len(paras) <= 4
    assert out.endswith("။")
    assert "Python\n" not in out + "\n" or not out.endswith("Python")
    assert out.count("စကားဝှက်") <= 1
    assert out.count("programming language") <= 2


def test_near_duplicate_prefix() -> None:
    text = (
        "Python ဆိုတာ programming language\n\n"
        "Python ဆိုတာ programming language တစ်ခု ဖြစ်ပါတယ်။\n\n"
        "ဥပမာ print(\"Hello\") လို့ ရေးရင် Hello ထွက်ပါတယ်။"
    )
    out = collapse_repeated_paragraphs(text)
    paras = [p for p in out.split("\n\n") if p.strip()]
    assert len(paras) == 2
    assert "Hello" in out


def test_gold_three_part_unchanged() -> None:
    gold = (
        "Python ဆိုတာ ကွန်ပျူတာကို ခိုင်းစေဖို့ ရေးတဲ့ programming language တစ်ခု ဖြစ်ပါတယ်။\n\n"
        "စာကြောင်းတွေက ဖတ်ရလွယ်အောင် ရေးထားလို့ စတင်သင်သူတွေ အသုံးများပါတယ်။\n\n"
        "ဥပမာ print(\"Hello\") လို့ ရေးရင် screen ပေါ်မှာ Hello ထွက်ပါတယ်။"
    )
    assert collapse_repeated_paragraphs(gold) == gold
