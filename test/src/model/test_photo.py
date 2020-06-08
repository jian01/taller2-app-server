import unittest
from src.model.photo import Photo
from PIL import Image
import base64
from io import BytesIO
import imagehash
from src.model.exceptions.not_an_image_exception import NotAnImageException

class TestUnitsPhoto(unittest.TestCase):
    def test_base64_not_photo(self):
        with self.assertRaises(NotAnImageException):
            Photo("asd")

    def test_target_crop_big_image(self):
        left, top, right, bottom = Photo.get_target_crop_square(1000,1000,200)
        self.assertEqual(left, 400)
        self.assertEqual(right, 600)
        self.assertEqual(top, 400)
        self.assertEqual(bottom, 600)

    def test_target_crop_small_image(self):
        left, top, right, bottom = Photo.get_target_crop_square(150,150,200)
        self.assertEqual(left, 0)
        self.assertEqual(right, 150)
        self.assertEqual(top, 0)
        self.assertEqual(bottom, 150)

    def test_from_file_big_jpg(self):
        with open("test_photos/big_jpg.jpg", "rb") as photo_file:
            photo = Photo.from_bytes(BytesIO(photo_file.read()))
        base64_img = photo.get_base64()
        image = Image.open(BytesIO(base64.b64decode(base64_img)))
        width, height = image.size
        self.assertEqual(width, 200)
        self.assertEqual(height, 200)
        with open("test_photos/big_jpg_target.jpg", "rb") as photo_file:
            target_image = Image.open(BytesIO(photo_file.read()))
        hash0 = imagehash.average_hash(image)
        hash1 = imagehash.average_hash(target_image)
        self.assertEqual(hash0 - hash1, 0)

    def test_from_file_thin_jpg(self):
        with open("test_photos/thin_jpg.jpg", "rb") as photo_file:
            photo = Photo.from_bytes(BytesIO(photo_file.read()))
        base64_img = photo.get_base64()
        image = Image.open(BytesIO(base64.b64decode(base64_img)))
        width, height = image.size
        self.assertEqual(width, 200)
        self.assertEqual(height, 200)
        with open("test_photos/thin_jpg_target.jpg", "rb") as photo_file:
            target_image = Image.open(BytesIO(photo_file.read()))
        hash0 = imagehash.average_hash(image)
        hash1 = imagehash.average_hash(target_image)
        self.assertEqual(hash0 - hash1, 0)

    def test_from_file_one_dimension_smaller_jpg(self):
        with open("test_photos/one_dimension_smaller.jpg", "rb") as photo_file:
            photo = Photo.from_bytes(BytesIO(photo_file.read()))
        base64_img = photo.get_base64()
        image = Image.open(BytesIO(base64.b64decode(base64_img)))
        width, height = image.size
        self.assertEqual(width, 200)
        self.assertEqual(height, 200)
        with open("test_photos/one_dimension_smaller_target.jpg", "rb") as photo_file:
            target_image = Image.open(BytesIO(photo_file.read()))
        hash0 = imagehash.average_hash(image)
        hash1 = imagehash.average_hash(target_image)
        self.assertEqual(hash0 - hash1, 0)