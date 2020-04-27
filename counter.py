import asyncio
import os
import json
import logging
from time import sleep
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import plural_ru
from telethon import TelegramClient, functions
from telethon.tl.functions.photos import DeletePhotosRequest, UploadProfilePhotoRequest
from telethon.tl.types import InputPhoto

from image_text import ImageText
from config import API_ID, API_HASH


logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


FONT_PATH = "lobster.ttf"
TEMPFILE_PATH = "output.jpg"
CACHE_PATH = "data.json"

TIME_PERIOD = timedelta(minutes=5)


class Storage:
    def __init__(self, path: str = CACHE_PATH, data=None):
        self.path = path = Path(path)

        if self.path.exists():
            self.load()
        else:
            if data is not None:
                self.data = data
            else:
                self.data = dict(date=datetime.today().astimezone().isoformat())
            self.save()

    def load(self):
        self.data = json.load(self.path.open())

    def save(self):
        json.dump(self.data, self.path.open("w"), indent=4)


def get_capture(time_delta: timedelta) -> str:
    days = time_delta.days
    hours = time_delta.seconds // 3600
    minutes = time_delta.seconds % 3600 // 60

    day_form = plural_ru.ru(days, ["день", "дня", "дней"])
    hour_form = plural_ru.ru(hours, ["час", "часа", "часов"])
    minute_form = plural_ru.ru(minutes, ["минута", "минуты", "минут"])

    return f"{days} {day_form} {hours} {hour_form} {minutes} {minute_form}"


async def update_counter(time_delta: timedelta, photo_id: Optional[int] = None) -> int:
    """Update avatar with number. Delete `photo_id` last avatar. Return new photo.id."""
    async with TelegramClient("Avatar counter", API_ID, API_HASH) as client:
        if photo_id is not None:
            photo = (await client.get_profile_photos("me"))[0]

            if photo.id == photo_id:
                await client(DeletePhotosRequest(
                    id=[InputPhoto(
                        id=photo.id,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference,
                    )]
                ))
            else:
                logger.warning("First run - getting last avatar")

        input_filename = await client.download_profile_photo("me")
        img = ImageText(input_filename)
        text = f"{get_capture(time_delta)} дома"
        img.write_text_box(
            (20, 520),
            text,
            box_width=600,
            font_filename=FONT_PATH,
            font_size=40,
            color=(255, 255, 255),
            place="center",
        )
        img.save(TEMPFILE_PATH)

        result = await client(
            UploadProfilePhotoRequest(
                file=await client.upload_file(TEMPFILE_PATH)
            )
        )

        os.remove(input_filename)
        os.remove(TEMPFILE_PATH)

        return result.photo.id


async def main():
    storage = Storage()

    while True:
        storage.load()
        date = datetime.fromisoformat(storage.data["date"]).astimezone()
        photo_id = storage.data.get("photo_id")
        new_photo_id = await update_counter(
            datetime.today().astimezone() - date,
            photo_id=photo_id if photo_id is None else int(photo_id),
        )
        storage.data["photo_id"] = new_photo_id
        storage.save()
        logger.info("Avatar changed going to sleep")
        sleep(TIME_PERIOD.total_seconds())


if __name__ == "__main__":
    asyncio.run(main())
