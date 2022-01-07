"""
Generate a tweet and send as a draft
"""
import argparse
import json
from pathlib import Path

import requests

HERE = Path(__file__).parent
TIPS_DIR = HERE / "../"


def gen_code_image(p_f90: Path):
    with open(p_f90) as f:
        code = f.read()

    data = json.dumps(
        {
            "code": code,
            "language": "Fortran",
            "theme": "one-light",
            "windowControls": False,
        }
    )

    r = requests.post(
        url="https://carbonara-42.herokuapp.com/api/cook",
        data=data,
        headers={"Content-Type": "application/json"},
        stream=True,
    )
    r.raise_for_status()

    # Save code image to file
    img = r.content  # response content is the image (bytes)
    with open("code.jpg", "wb") as f:
        f.write(r.content)

    return img


def main(tip: str, *, draft: bool):
    # Check for the relevant file(s)
    p = TIPS_DIR / f"{tip}.f90"
    tip_f90 = p if p.is_file() else None
    p = TIPS_DIR / f"{tip}.txt"
    tip_txt = p if p.is_file() else None

    if tip_f90 is None and tip_txt is None:
        raise ValueError(f"neither .f90 nor .txt found for {tip!r}")

    # Create code image
    if tip_f90 is not None:
        code_image = gen_code_image(tip_f90)

    # Extract tweet text
    if tip_txt is not None:
        with open(tip_txt, "r") as f:
            tweet_text = f.read().split("Long version\n===")[0].rstrip()
            print(tweet_text)

    # Create tweet draft???
    if draft:
        raise NotImplementedError
        # Upload code image to @FortranTip Media Library
        ...

        # # Create draft post
        # r = requests.post(
        #     url="https://ads-api.twitter.com/10/accounts/:account_id/draft_tweets"
        # )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "tip", 
        help="tip file stem (e.g., `hello_world`, `assoc`, `array_intrinsics`)"
    )
    parser.add_argument("--draft", action="store_true", help="post Tweet draft")
    args = parser.parse_args()

    main(args.tip, draft=args.draft)
