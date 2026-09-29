"""Manual one-book vocabulary detector check."""
import sys

if __package__:
    from tools.vocab_detector import detect_vocab_in_book
else:
    from vocab_detector import detect_vocab_in_book

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "初中/人教版/七年级/下册（2024年度）"
    print(f"Testing detect_vocab_in_book on: {target}")
    res = detect_vocab_in_book(target, force_refresh=True)
    print(f"Result summary: {res['summary']}")
    print(f"Vocab count: {res['vocab_count']}, Non-vocab count: {res['non_vocab_count']}")
    if res['detected']:
        print(f"Start file: {res['start_file']}, End file: {res['end_file']}")
