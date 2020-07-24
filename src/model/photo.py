from io import BytesIO
import base64
from PIL import Image
import math
from typing import Tuple, Optional
from src.model.exceptions.not_an_image_exception import NotAnImageException

SQUARE_IMAGE_TARGET = 200
DEFAULT_PHOTO = "iVBORw0KGgoAAAANSUhEUgAAAMgAAADIBAMAAABfdrOtAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAwUExURWJ4hsvV3gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP2efMkAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAHDSURBVHja7dpLbgQhDATQ4gZw/8tGSRaJEj7Grnb3MMUa6anMjADTaAlDiBAhQoQIESJEiBAhQoQIESIkguB7lAuRip9RrkF+E5/jCuSvsaHAb9gV+8TOKGSkF8SsIGJYC2adNhiFiIyCGKMYZyEUxYSMg9ii2CYhFsWCzIKYosSRwkGQgMyDWOpFQAoDwSnIqlqGRTHMQDjKGyHrJVkvyusgJYpACBtBEKlC+EiJIRAi5CrE9gte/VGECBEiRIgQIRuITivviuimtYUcdI8/p0t0UHswpZua03xO6dWnvDrkPNKkPDflvM5NlEZEWiBHiz2Vs1+xO4z9A4YN5Gv6NuBAfEOIECFC7kX2NisP4tgTdxH/nhX89IqLAJFN/jlHIiCmPOUsDEQVxk0rjmRcTFM6EiYj2CUCGMocsfY5FwUDJcgiCjhB5lHACTKPAlKQqQJSEMwKBpoxiUJE4EBqBrJtjOsFXpBxFPCCjKNQEWwiFcQoYAbZRHxBRvUCM8goyo2It1qDet2IuI1+vcAN0o9yHxIwuvV6TQRGpD4fKTYEz0dgQuoxSNDoLMrJSHRJOotyMhI2/i+KkBhSXwTBqUhrH/inqKSqOb7ZAAAAAElFTkSuQmCC"

class Photo:
    def __init__(self, base64_img: Optional[str] = None):
        if not base64_img:
            base64_img = DEFAULT_PHOTO
        try:
            Image.open(BytesIO(base64.b64decode(base64_img)))
        except Exception:
            raise NotAnImageException
        self.photo_base64 = base64_img

    @staticmethod
    def get_target_crop_square(width, height, target) -> Tuple[int, int, int, int]:
        """
        Gets the crop sides for cropping a square of target x target

        :param width: the width of the image
        :param height: the height of the image
        :param target: the target height and width
        """
        if width < target or height < target:
            target = min(width, height)
        half_target = math.floor(target/2)
        middle_width = width/2
        middle_height = height/2
        left = math.floor(max(middle_width - half_target, 0))
        top = math.floor(max(middle_height - half_target, 0))
        right = math.floor(min(middle_width + half_target, width))
        bottom = math.floor(min(middle_height + half_target, height))
        return left, top, right, bottom


    @classmethod
    def from_bytes(cls, photo: BytesIO):
        image = Image.open(photo).convert("RGB")
        width, height = image.size
        ratio = width/height
        if width < height:
            image = image.resize((SQUARE_IMAGE_TARGET, math.floor(SQUARE_IMAGE_TARGET/ratio)), Image.ANTIALIAS)
        else:
            image = image.resize((math.floor(SQUARE_IMAGE_TARGET*ratio), SQUARE_IMAGE_TARGET), Image.ANTIALIAS)
        width, height = image.size
        left, top, right, bottom = cls.get_target_crop_square(width, height, SQUARE_IMAGE_TARGET)
        image = image.crop((left, top, right, bottom))
        image = image.resize((SQUARE_IMAGE_TARGET, SQUARE_IMAGE_TARGET), Image.ANTIALIAS)

        buffered = BytesIO()
        image.save(buffered, quality=90, format="JPEG")
        return cls(base64.b64encode(buffered.getvalue()).decode())

    def get_base64(self) -> str:
        return self.photo_base64