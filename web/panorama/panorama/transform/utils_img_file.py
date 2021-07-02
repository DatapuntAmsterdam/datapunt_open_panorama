import io
import os

from numpy import squeeze, dsplit, dstack, array
from pathlib import Path
from scipy import misc
from scipy.ndimage import map_coordinates
from PIL import Image, ImageOps
import cv2

from panorama.shared.object_store import ObjectStore

PANORAMA_WIDTH = 8000
PANORAMA_HEIGHT = 4000
SAMPLE_WIDTH = 480
SAMPLE_HEIGHT = 320

object_store = ObjectStore()


def image2byte_array(image: Image, quality=80):
    """
    Translate PIL image to byte array
    :param image: PIL image
    :return: bytearray
    """
    img_byte_array = io.BytesIO()
    image.save(img_byte_array, quality=quality, format='JPEG')
    return img_byte_array.getvalue()


def image2byte_array_sized(image: Image, size=1000000):
    """
    Translate PIL image to byte array with maximum file size (deault 1MB)
    :param image: the PIL image
    :param size: maximum file size
    :return:
    """
    for quality in range(80, 0, -10):
        byte_array = image2byte_array(image, quality=quality)
        if len(byte_array) < size:
            return byte_array

    raise Exception('Could not create small enough image')


def byte_array2image(byte_array):
    """
    Translate byte array to PIL image
    :param byte_array:
    :return: PIL image
    """
    return Image.open(io.BytesIO(byte_array))


def get_raw_panorama_image(panorama_path):
    """
    Gets the un-rendered, un-blurred source image from the source container

    :param panorama_path: path of the image
    :return: PIL image
    """

    # construct objectstore_id
    container = panorama_path.split('/')[0]
    name = panorama_path.replace(container + '/', '')
    objectstore_id = {'container': container, 'name': name}

    return byte_array2image(object_store.get_panorama_store_object(objectstore_id))


def get_intermediate_panorama_image(panorama_path):
    """
    Gets the rendered, but un-blurred intermediate image from the

    :param panorama_path: path of the image
    :return: PIL image
    """

    objectstore_id = {'container': 'intermediate', 'name': panorama_path}
    return byte_array2image(object_store.get_panorama_store_object(objectstore_id))


def get_panorama_image(panorama_path):
    """
    Gets the rendered, blurred result image of the panorama

    :param panorama_path: path of the image
    :return: PIL image
    """
    return byte_array2image(object_store.get_datapunt_store_object(panorama_path))


def get_rgb_channels_from_array_image(array_img):
    """
    Orders the dimensions of the scipy image array around, so that it becomes an array of three color channels

    :param array_img: image array
    :return: reordered image array
    """
    # split image in the 3 RGB channels
    return squeeze(dsplit(array_img, 3))


def get_raw_panorama_as_rgb_array(panorama_path):
    """
    Gets the raw image prepared for calculations.

    :param panorama_path: path of the image
    :return: scipy image array, an array of three color channels
    """
    # read image as scipy rgb image array
    panorama_array_image = misc.fromimage(get_raw_panorama_image(panorama_path))
    return get_rgb_channels_from_array_image(panorama_array_image)


def sample_rgb_array_image_as_array(coordinates, rgb_array):
    """
    Resampling of the source image

    :param coordinates: meshgrid of numpy arrays where eacht target coordinate is mapped to a coordinateset
    of the source
    :param rgb_array: the source image as a scipy rgb array representation
    :return: the sampled target image as a scipy rgb array representation
    """
    x = coordinates[0]
    y = coordinates[1]

    # resample each channel of the source image
    #   (this needs to be done 'per channel' because otherwise the map_coordinates method
    #    works on the wrong dimension: in rgb_array_images from scipy.misc.fromimage the
    #    first dimension is the channel (r, g and b), and 2nd and 3rd dimensions are y and x,
    #    but map_coordinates expects the the coordinates to map to to be 1st and 2nd, therefore
    #    we extract each channel, so that y and x become 1st and 2nd array), after resampling
    #    we stack the three channels on top of each other, to restore the rgb image array

    r = map_coordinates(rgb_array[0], [y, x], order=1)
    g = map_coordinates(rgb_array[1], [y, x], order=1)
    b = map_coordinates(rgb_array[2], [y, x], order=1)

    # merge channels
    return dstack((r, g, b))


def save_image(image, name, in_panorama_store=False):
    """
    Save an PIL image in the objectstore

    :param image: PIL image to save
    :param name: path to save the image at
    :param in_panorama_store: flag for choosing specific store
    """

    if True:
        blurred_base = '/Users/bart/Development/datapunt/github.com/panorama/blurred'
        path = os.path.join(blurred_base, name)
        Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
        image.save(path, format='JPEG', optimize=True, progressive=True)

    else:
        byte_array = io.BytesIO()
        image.save(byte_array, format='JPEG', optimize=True, progressive=True)
        if in_panorama_store:
            container, name = name.split('/')[0], '/'.join(name.split('/')[1:])
            object_store.put_into_panorama_store(container, name, byte_array.getvalue(), 'image/jpeg')
        else:
            object_store.put_into_datapunt_store(name, byte_array.getvalue(), 'image/jpeg')


def save_array_image(array_img, name, in_panorama_store=False):
    """
    Save a scipy image array in the objectstore

    :param array_img: scipy image array to save
    :param name: path to save the image at
    :param in_panorama_store: flag for choosing specific store
    """
    save_image(Image.fromarray(array_img), name, in_panorama_store)


def roll_left(image, shift, width, height):
    """
    Utility method to wrap an image around to the left

    :param image: PIL image to wrap around
    :param shift: the amount of pixels to shift
    :param width:  width of the image
    :param height: height of the image
    :return: shifted PIL image
    """
    part1 = image.crop((0, 0, shift, height))
    part2 = image.crop((shift, 0, width, height))
    part1.load()
    part2.load()
    output = Image.new('RGB', (width, height))
    output.paste(part2, (0, 0, width-shift, height))
    output.paste(part1, (width-shift, 0, width, height))

    return output


def sample_image(image, x, y, sample_width=SAMPLE_WIDTH, sample_height=SAMPLE_HEIGHT):
    """
    Utility method to take a sample from an image

    :param image: PIL image to sample from
    :param x: left-top-x of sample
    :param y: left-top-y of sample
    :param sample_width: width of sample
    :param sample_height: height of sample
    :return:
    """
    if PANORAMA_WIDTH < x + sample_width:
        intermediate = roll_left(image, sample_width, PANORAMA_WIDTH, PANORAMA_HEIGHT)
        snippet = intermediate.crop((x - sample_width, y, x, y + sample_height))
    else:
        snippet = image.crop((x, y, x + sample_width, y + sample_height))
    return snippet


def prepare_img(snippet, zoom, for_cv=True):
    """
    Prepare an image-snippet for detection (of licensplate or face)

    :param snippet: snippet of PIL image
    :param zoom: zoom-factor
    :param for_cv: flag for preparing in OpenCV (default)
    :return: equalized and zoomed snippet
    """
    zoomed_size = (int(zoom*SAMPLE_WIDTH), int(zoom*SAMPLE_HEIGHT))
    zoomed_snippet = snippet.resize(zoomed_size, Image.BICUBIC)
    if not for_cv:
        return ImageOps.equalize(zoomed_snippet)
    else:
        gray_image = cv2.cvtColor(array(zoomed_snippet), cv2.COLOR_RGB2GRAY)
        return cv2.equalizeHist(gray_image)
