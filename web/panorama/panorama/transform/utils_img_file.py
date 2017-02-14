import io

from numpy import squeeze, dsplit, dstack, array
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


def image2byte_array(image: Image):
    img_byte_array = io.BytesIO()
    image.save(img_byte_array, format='JPEG')
    return img_byte_array.getvalue()


def byte_array2image(byte_array):
    return Image.open(io.BytesIO(byte_array))


def get_raw_panorama_image(panorama_path):
    # construct objectstore_id
    container = panorama_path.split('/')[0]
    name = panorama_path.replace(container + '/', '')
    objectstore_id = {'container': container, 'name': name}

    return byte_array2image(object_store.get_panorama_store_object(objectstore_id))


def get_panorama_image(panorama_path):
    return byte_array2image(object_store.get_datapunt_store_object(panorama_path))


def get_rgb_channels_from_array_image(array_img):
    # split image in the 3 RGB channels
    return squeeze(dsplit(array_img, 3))


def get_raw_panorama_as_rgb_array(panorama_path):
    # read image as numpy array
    panorama_array_image = misc.fromimage(get_raw_panorama_image(panorama_path))
    return get_rgb_channels_from_array_image(panorama_array_image)


def sample_rgb_array_image_as_array(coordinates, rgb_array):
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
    byte_array = io.BytesIO()
    image.save(byte_array, format='JPEG', optimize=True, progressive=True)
    if in_panorama_store:
        container, name = name.split('/')[0], '/'.join(name.split('/')[1:])
        object_store.put_into_panorama_store(container, name, byte_array.getvalue(), 'image/jpeg')
    else:
        object_store.put_into_datapunt_store(name, byte_array.getvalue(), 'image/jpeg')


def save_array_image(array_img, name, in_panorama_store=False):
    save_image(Image.fromarray(array_img), name, in_panorama_store)


def roll_left(image, shift, width, height):
    part1 = image.crop((0, 0, shift, height))
    part2 = image.crop((shift, 0, width, height))
    part1.load()
    part2.load()
    output = Image.new('RGB', (width, height))
    output.paste(part2, (0, 0, width-shift, height))
    output.paste(part1, (width-shift, 0, width, height))

    return output


def sample_image(image, x, y, sample_width=SAMPLE_WIDTH, sample_height=SAMPLE_HEIGHT):
    if PANORAMA_WIDTH < x + sample_width:
        intermediate = roll_left(image, sample_width, PANORAMA_WIDTH, PANORAMA_HEIGHT)
        snippet = intermediate.crop((x - sample_width, y, x, y + sample_height))
    else:
        snippet = image.crop((x, y, x + sample_width, y + sample_height))
    return snippet


def prepare_img(snippet, zoom, for_cv=True):
    zoomed_size = (int(zoom*SAMPLE_WIDTH), int(zoom*SAMPLE_HEIGHT))
    zoomed_snippet = snippet.resize(zoomed_size, Image.BICUBIC)
    if not for_cv:
        return ImageOps.equalize(zoomed_snippet)
    else:
        gray_image = cv2.cvtColor(array(zoomed_snippet), cv2.COLOR_RGB2GRAY)
        return cv2.equalizeHist(gray_image)