# -*- coding: utf-8 -*-

'''
The MIT License (MIT)

Copyright (c) 2021-present Buster

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
'''

from collections import defaultdict
from itertools import chain
from pathlib import Path
from random import randrange
from typing import BinaryIO, List, Union

from PIL import Image


class TransparentAnimatedGifConverter:
    '''Copied from https://gist.github.com/egocarib/ea022799cca8a102d14c54a22c45efe0 because PIL support is shit'''
    _PALETTE_SLOTSET = set(range(256))

    def __init__(self, img_rgba: Image, alpha_threshold: int = 0):
        self._img_rgba = img_rgba
        self._alpha_threshold = alpha_threshold

    def _process_pixels(self):
        '''Set the transparent pixels to the color 0.'''
        self._transparent_pixels = {
            idx for idx, alpha in enumerate(
                self._img_rgba.getchannel(channel='A').getdata()
            ) if alpha <= self._alpha_threshold
        }

    def _set_parsed_palette(self):
        '''Parse the RGB palette color `tuple`s from the palette.'''
        palette = self._img_p.getpalette()
        self._img_p_used_palette_idxs = {
            idx for pal_idx, idx in enumerate(self._img_p_data)
            if pal_idx not in self._transparent_pixels
        }

        self._img_p_parsedpalette = {
            idx: tuple(palette[idx * 3 : idx * 3 + 3])
            for idx in self._img_p_used_palette_idxs
        }

    def _get_similar_color_idx(self):
        '''Return a palette index with the closest similar color.'''
        old_color = self._img_p_parsedpalette[0]
        dict_distance = defaultdict(list)
        for idx in range(1, 256):
            color_item = self._img_p_parsedpalette[idx]
            if color_item == old_color:
                return idx
            distance = sum((
                abs(old_color[0] - color_item[0]),
                abs(old_color[1] - color_item[1]),
                abs(old_color[2] - color_item[2])))
            dict_distance[distance].append(idx)
        return dict_distance[sorted(dict_distance)[0]][0]

    def _remap_palette_idx_zero(self):
        '''Since the first color is used in the palette, remap it.'''
        free_slots = self._PALETTE_SLOTSET - self._img_p_used_palette_idxs
        new_idx = free_slots.pop() if free_slots else self._get_similar_color_idx()
        self._img_p_used_palette_idxs.add(new_idx)
        self._palette_replaces['idx_from'].append(0)
        self._palette_replaces['idx_to'].append(new_idx)
        self._img_p_parsedpalette[new_idx] = self._img_p_parsedpalette[0]
        del self._img_p_parsedpalette[0]

    def _get_unused_color(self) -> tuple:
        '''Return a color for the palette that does not collide with any other already in the palette.'''
        used_colors = set(self._img_p_parsedpalette.values())
        while True:
            new_color = (randrange(256), randrange(256), randrange(256))
            if new_color not in used_colors:
                return new_color

    def _process_palette(self):
        '''Adjust palette to have the zeroth color set as transparent. Basically, get another palette
        index for the zeroth color.
        '''
        self._set_parsed_palette()
        if 0 in self._img_p_used_palette_idxs:
            self._remap_palette_idx_zero()
        self._img_p_parsedpalette[0] = self._get_unused_color()

    def _adjust_pixels(self):
        '''Convert the pixels into their new values.'''
        if self._palette_replaces['idx_from']:
            trans_table = bytearray.maketrans(
                bytes(self._palette_replaces['idx_from']),
                bytes(self._palette_replaces['idx_to'])
            )
            self._img_p_data = self._img_p_data.translate(trans_table)
        for idx_pixel in self._transparent_pixels:
            self._img_p_data[idx_pixel] = 0
        self._img_p.frombytes(data=bytes(self._img_p_data))

    def _adjust_palette(self):
        '''Modify the palette in the new `Image`.'''
        unused_color = self._get_unused_color()
        final_palette = chain.from_iterable(
            self._img_p_parsedpalette.get(x, unused_color)
            for x in range(256)
        )
        self._img_p.putpalette(data=final_palette)

    def process(self) -> Image:
        '''Return the processed mode `P` `Image`.'''
        self._img_p = self._img_rgba.convert(mode='P')
        self._img_p_data = bytearray(self._img_p.tobytes())
        self._palette_replaces = dict(idx_from=list(), idx_to=list())
        self._process_pixels()
        self._process_palette()
        self._adjust_pixels()
        self._adjust_palette()
        self._img_p.info['transparency'] = 0
        self._img_p.info['background'] = 0
        return self._img_p


def _create_animated_gif(images, durations):
    '''If the image is a GIF, create an its thumbnail here.'''
    save_kwargs = {}
    new_images = []

    for frame in images:
        thumbnail = frame.copy()
        thumbnail_rgba = thumbnail.convert(mode='RGBA')
        thumbnail_rgba.thumbnail(size=frame.size, reducing_gap=3.0)
        converter = TransparentAnimatedGifConverter(img_rgba=thumbnail_rgba)
        thumbnail_p = converter.process()
        new_images.append(thumbnail_p)

    output_image = new_images[0]
    save_kwargs.update(
        format='GIF',
        save_all=True,
        optimize=False,
        append_images=new_images[1:],
        duration=durations,
        disposal=2,
        loop=0
    )
    return output_image, save_kwargs


def save_transparent_gif(images: List[Image.Image], durations: Union[int, List[int]], save_file: Union[str, Path, BinaryIO]):
    '''Creates a transparent GIF, adjusting to avoid transparency issues
    that are present in the PIL library

    Parameters
    ----------
    images : List[Image.Image]
        A list of PIL Image objects that compose the GIF frames
    durations : Union[int, List[int]]
        The animation durations for the frames of this GIF
    save_file : Union[str, Path, BinaryIO]
        Where to save the end result to (as passed to `PIL.Image.save()`)
    '''
    root_frame, save_args = _create_animated_gif(images, durations)
    root_frame.save(save_file, **save_args)
