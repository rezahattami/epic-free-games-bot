
import requests
import json
import os
import asyncio

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from telegram import Bot
from telegram.request import HTTPXRequest


# ============================================================
# TELEGRAM
# ============================================================

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

CHANNEL_ID = "@freegamesalertt"


# ============================================================
# EPIC API
# ============================================================

URL = (
    "https://store-site-backend-static-ipv4.ak.epicgames.com/"
    "freeGamesPromotions"
    "?locale=en-US&country=US&allowCountries=US"
)


SENT_FILE = "sent_games.json"


# ============================================================
# GET EPIC GAMES
# ============================================================

def get_games():

    r = requests.get(
        URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    r.raise_for_status()

    data = r.json()

    return (
        data["data"]
        ["Catalog"]
        ["searchStore"]
        ["elements"]
    )


# ============================================================
# SENT GAMES
# ============================================================

def get_sent():

    if not os.path.exists(SENT_FILE):
        return []

    try:

        with open(
            SENT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, list):
                return data

    except Exception:
        pass

    return []


def save_sent(data):

    with open(
        SENT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# IMAGE
# ============================================================

def get_image(game):

    images = game.get(
        "keyImages",
        []
    )

    preferred_types = [
        "OfferImageWide",
        "DieselStoreFrontWide"
    ]

    for image_type in preferred_types:

        for img in images:

            if img.get("type") == image_type:

                url = img.get("url")

                if url:
                    return url

    for img in images:

        url = img.get("url")

        if url:
            return url

    return None


# ============================================================
# FREE END DATE
# ============================================================

def get_free_end(game):

    promotions = (
        game.get("promotions")
        or {}
    )

    offers = (
        promotions.get(
            "promotionalOffers"
        )
        or []
    )

    # Epic API uses UTC time
    now = datetime.now(
        timezone.utc
    )

    for group in offers:

        for offer in group.get(
            "promotionalOffers",
            []
        ):

            discount = (
                offer
                .get("discountSetting", {})
                .get("discountPercentage")
            )

            if discount != 0:
                continue

            start = offer.get(
                "startDate"
            )

            end = offer.get(
                "endDate"
            )

            if not start or not end:
                continue

            try:

                start_date = datetime.fromisoformat(
                    start.replace(
                        "Z",
                        "+00:00"
                    )
                )

                end_date = datetime.fromisoformat(
                    end.replace(
                        "Z",
                        "+00:00"
                    )
                )

            except Exception:

                continue

            if start_date <= now <= end_date:

                return end_date

    return None


# ============================================================
# EPIC STORE LINK
# ============================================================

def create_link(game):

    # 1. Normal productSlug

    slug = game.get(
        "productSlug"
    )

    if slug:

        return (
            "https://store.epicgames.com/en-US/p/"
            + slug
        )

    # 2. urlSlug

    slug = game.get(
        "urlSlug"
    )

    if slug:

        return (
            "https://store.epicgames.com/en-US/p/"
            + slug
        )

    # 3. catalogNs mappings

    catalog_ns = (
        game.get("catalogNs")
        or {}
    )

    mappings = (
        catalog_ns.get(
            "mappings"
        )
        or []
    )

    for mapping in mappings:

        page_slug = mapping.get(
            "pageSlug"
        )

        if page_slug:

            return (
                "https://store.epicgames.com/en-US/p/"
                + page_slug
            )

    # 4. No link found

    return (
        "🔗 Store link will be added soon"
    )


# ============================================================
# POST TEXT
# ============================================================

def create_text(
    game,
    end
):

    title = game.get(
        "title",
        "Unknown"
    )

    # Convert Epic UTC time to UTC
    utc_time = end.astimezone(
        timezone.utc
    )

    link = create_link(
        game
    )

    return (
        "🎁 FREE GAME AVAILABLE\n"
        "\n"
        f"🎮 {title}\n"
        "\n"
        "🏪 Store:\n"
        "Epic Games Store\n"
        "\n"
        "⏰ Available until:\n"
        f"{utc_time.strftime('%Y/%m/%d - %H:%M')} "
        "UTC time\n"
        "\n"
        f"{link}\n"
        "\n"
        "#FreeGames #EpicGames"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 60)
    print("🎮 EPIC FREE GAME TELEGRAM BOT")
    print("=" * 60)

    if (
        not TOKEN
        or TOKEN == "PUT_YOUR_NEW_BOT_TOKEN_HERE"
    ):

        print()
        print(
            "❌ Please set your new Telegram bot token."
        )

        return

    request = HTTPXRequest(
        connect_timeout=60,
        read_timeout=60,
        write_timeout=60
    )

    bot = Bot(
        token=TOKEN,
        request=request
    )

    games = get_games()

    sent = get_sent()

    posted = False

    for game in games:

        title = game.get(
            "title",
            ""
        ).strip()

        if not title:
            continue

        # Ignore bundles

        if "bundle" in title.lower():
            continue

        # Ignore already posted games

        if title in sent:
            continue

        end = get_free_end(
            game
        )

        if not end:
            continue

        text = create_text(
            game,
            end
        )

        image = get_image(
            game
        )

        try:

            if image:

                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=image,
                    caption=text
                )

            else:

                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=text
                )

            sent.append(
                title
            )

            save_sent(
                sent
            )

            print(
                "Posted:",
                title
            )

            posted = True

        except Exception as e:

            print(
                "❌ Telegram error:",
                e
            )

    if not posted:

        print(
            "No new free games"
        )


if __name__ == "__main__":

    asyncio.run(
        main()
    )

