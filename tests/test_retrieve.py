from tutor.prompts import build_user_content
from tutor.retrieve import retrieve_book_quotes

BINARY_SEARCH = '''
def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = low + (high - low) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
'''


def test_binary_search_retrieve_skips_bit_byte() -> None:
    quotes = retrieve_book_quotes("ဒီ code ကို ရှင်းပြပါ။", BINARY_SEARCH)
    blob = "\n".join(quotes)
    assert "00000000" not in blob
    assert "1 Byte" not in blob


def test_quotes_injected_only_when_present() -> None:
    text = build_user_content(
        "Python ဆိုတာ ဘာလဲ?",
        "",
        ["Programmer တွေဟာ programming language တစ်ခုခု ကို အသုံးပြုပြီး app တွေကို ဖန်တီးကြပါတယ်။"],
    )
    assert "စာအုပ်မှ ကိုးကား:" in text
    plain = build_user_content("Python ဆိုတာ ဘာလဲ?", "")
    assert "စာအုပ်မှ ကိုးကား:" not in plain
