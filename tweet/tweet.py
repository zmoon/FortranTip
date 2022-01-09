"""
Generate and post a tweet for @FortranTip
"""
import argparse
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session  # type: ignore[import]
from rich import print
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn
from rich.syntax import Syntax

HERE = Path(__file__).parent
TIPS_DIR = HERE / "../"


def _maybe_path(p: Path) -> Optional[Path]:
    "Check if it exists"
    return p if p.is_file() else None


@contextmanager
def _progress(txt: str):
    with Progress(
        f"[italic]{txt} ... ",
        SpinnerColumn(finished_text="[green]Done!"),
        transient=False,
    ) as progress:
        task = progress.add_task("", total=1)  # couldn't get this descrip to show up
        try:
            yield
        finally:
            progress.advance(task, 1)


def gen_code_image(code: str, *, save: bool = True) -> bytes:
    payload = {
        "code": code,
        "language": "Fortran",
        "theme": "one-light",
        "windowControls": False,
        "backgroundColor": "rgba(255, 255, 255, 100)",
    }

    r = requests.post(
        url="https://carbonara-42.herokuapp.com/api/cook",
        json=payload,
        stream=True,
    )
    r.raise_for_status()

    # Save code image to file
    img = r.content  # response content is the image (bytes)
    if save:
        with open(HERE / "code.jpg", "wb") as f:
            f.write(r.content)

    return img


def post_tweet(tweet_text: str, code_image: Optional[bytes]) -> None:
    if not os.environ.get("GITHUB_ACTIONS"):
        p_env = HERE / ".env"
        assert p_env.is_file(), f".env file is needed"
        load_dotenv(p_env)

    CK = os.environ.get("TWITTER_CK")
    CS = os.environ.get("TWITTER_CS")
    AT = os.environ.get("TWITTER_AT")
    AS = os.environ.get("TWITTER_AS")

    twitter = OAuth1Session(CK, CS, AT, AS)

    payload: Dict[str, Any] = {"text": tweet_text}

    if code_image is not None:
        with _progress("Uploading code image to Twitter"):
            r_media = twitter.post(
                url="https://upload.twitter.com/1.1/media/upload.json",
                files={"media": code_image},
            )
        r_media.raise_for_status()
        media_id = str(json.loads(r_media.text)["media_id"])
        payload.update(media={"media_ids": [media_id]})

    # Check that we have something
    if not payload["text"].strip() and payload.get("media") is None:
        raise ValueError("this tweet will be empty")

    # Post
    with _progress("Posting Tweet to Twitter"):
        r_tweet = twitter.post(
            "https://api.twitter.com/2/tweets",
            json=payload,
        )
    r_tweet.raise_for_status()


def main(tip: str, *, dry_run: bool = False, image_only: bool = False):
    # Check for the relevant file(s)
    p_tip_f90 = _maybe_path(TIPS_DIR / f"{tip}.f90")
    p_tip_txt = _maybe_path(TIPS_DIR / f"{tip}.txt")
    if p_tip_f90 is None and p_tip_txt is None:
        raise ValueError(
            f"neither {tip}.f90 nor {tip}.txt found in {TIPS_DIR.resolve().as_posix()}"
        )

    # Create code image
    code_image = None
    if p_tip_f90 is not None:
        with open(p_tip_f90) as f:
            code = f.read()
        if dry_run:
            print(Panel(Syntax(code, "fortran"), expand=False, title="Fortran code"))
        else:
            with _progress("Generating code image"):
                code_image = gen_code_image(code)

    # Optional early exit
    if image_only:
        if code_image is None:
            raise ValueError(f"--image-only used but {tip}.f90 was not found")
        return

    # Extract tweet text
    tweet_text = ""
    if p_tip_txt is not None:
        with open(p_tip_txt, "r") as f:
            tweet_text = f.read().split("Long version\n===")[0].rstrip()
    if dry_run:
        print(Panel(tweet_text, title="Tweet text"))

    # Tweet
    if not dry_run:
        post_tweet(tweet_text, code_image)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="generate and post a tweet for @FortranTip")
    parser.add_argument(
        "tip",
        help="tip file stem (e.g., `hello_world`, `assoc`, `array_intrinsics`)",
    )
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="show what would be done"
    )
    parser.add_argument(
        "-i", "--image-only", action="store_true", help="only generate the code image",
    )

    args = parser.parse_args()

    main(args.tip, dry_run=args.dry_run, image_only=args.image_only)
