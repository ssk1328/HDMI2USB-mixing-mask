#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

"""
This module defines Python classes and methods to define a approach for run
length encoding of rgb pixel data. 
"""

import struct
from collections import namedtuple
from PIL import Image
import numpy as np 


REPEAT_OP = 1
PIXEL_OP = 2


class Pixel(int):

    """
    This defines a defines a new Pixel class to represent rgb pixel data. The class
    defines methods for generating and encoding the the given Pixel data.

    >>> Pixel(1).gen()
    [1]
    >>> Pixel(5).gen()
    [5]
    """

    def __new__(cls, value):
        """
        Static method defined to assert the value to take values only integer 
        the range 0-255
        """
        assert value >= 0
        assert value < 256
        return int.__new__(cls, value)

    def gen(self):
        """
        Method defined to return the pixel value of the object as a list of integer. 

        >>> Pixel(0).gen()
        [0]
        >>> Pixel(128).gen()
        [128]
        """
        return [int(self)]

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, int.__repr__(self))

    def encode(self):
        """
        Method defined which returns a string in an encoded representation for an
        given object of Pixel class. A pixel object is encoded as a four byte 
        string, of which the first byte is pixel op code PIXEL_OP, and rest 
        three bytes represents rgb pixel data of the pixel.

        >>> Pixel(0).encode()
        '\\x02\\x00\\x00\\x00'
        >>> Pixel(0x10).encode()
        '\\x02\\x10\\x10\\x10'
        """
        return struct.pack("<BBBB", PIXEL_OP, self, self, self)


WHITE = Pixel(255)
BLACK = Pixel(0)

_RepeatBase = namedtuple("Repeat", ["count", "contents"])


class Repeat(_RepeatBase):

    """
    This class defines a way to write run length encoded pixel data in a compact nested form.

    Repeat is inherited from _RepeatBase namedtuple which takes two arguments

    - **parameters**, **types**, **return** and **return types**::    

        :param arg1: Number of times the content value has to repeated
        :param arg2: List of contents can be an object of Repeat or Pixel class 
        :type arg1: int
        :type arg1: list of Repeat or Pixel object
        :return: A object of Repeat class
        :rtype: class.Repeat

    >>> Repeat(1, [Pixel(1)]).gen()
    [1]
    >>> Repeat(5, [Pixel(1)]).gen()
    [1, 1, 1, 1, 1]
    >>> Repeat(1, [Pixel(1), Pixel(10)]).gen()
    [1, 10]
    >>> Repeat(3, [Pixel(1), Pixel(10)]).gen()
    [1, 10, 1, 10, 1, 10]
    """

    def __new__(cls, *args):
        if len(args) == 1:
            args = args[0]
        return _RepeatBase.__new__(cls, *args)

    def gen(self):
        contents = []
        for i in self.contents:
            contents += i.gen()
        return int(self.count) * contents

    def __repr__(self):
        return "Repeat(%r, %r)" % (self.count, self.contents)

    def encode(self):
        """
        >>> Repeat(1, []).encode()
        '\\x01\\x00\\x01\\x00'
        >>> Repeat(2, [Pixel(0)]).encode()
        '\\x01\\x01\\x02\\x00\\x02\\x00\\x00\\x00'
        >>> Repeat(3000, [Repeat(2000, [Pixel(1)]), Pixel(12), Pixel(23)]).encode()
        '\\x01\\x03\\xb8\\x0b\\x01\\x01\\xd0\\x07\\x02\\x01\\x01\\x01\\x02\\x0c\\x0c\\x0c\\x02\\x17\\x17\\x17'
        """
        data = [struct.pack("<BBH", REPEAT_OP, len(self.contents), self.count)]
        assert len(data[0]) == 4
        for i in self.contents:
            data.append(i.encode())
        return "".join(data)


def DecodeBytes(data):
    """
    >>> DecodeBytes('\\x01\\x00\\x01\\x00')
    (Repeat(1, []), '')
    >>> DecodeBytes('\\x02\\x00\\x00\\x00')
    (Pixel(0), '')
    >>> DecodeBytes('\\x01\\x01\\x02\\x00\\x02\\x00\\x00\\x00')
    (Repeat(2, [Pixel(0)]), '')
    >>> DecodeBytes('\\x01\\x03\\xb8\\x0b\\x01\\x01\\xd0\\x07\\x02\\x01\\x01\\x01\\x02\\x0c\\x0c\\x0c\\x02\\x17\\x17\\x17')
    (Repeat(3000, [Repeat(2000, [Pixel(1)]), Pixel(12), Pixel(23)]), '')
    """
    op, data = data[:4], data[4:]
    assert len(op) == 4, op
    optype, = struct.unpack("B", op[0])
    if optype == PIXEL_OP:
        r, g, b, = struct.unpack("<BBB", op[1:])
        assert r == g == b
        return Pixel(r), data
    elif optype == REPEAT_OP:
        elements, times = struct.unpack("<BH", op[1:])
        assert elements >= 0
        assert times >= 0
        contents = []
        for i in range(0, elements):
            a, data = DecodeBytes(data)
            contents.append(a)
        return Repeat(times, contents), data
    assert False, (optype, data)


# Template([Repeat(720, lambda t: 1280-t, [BLACK]), Repeat(lambda t: t,
# [WHITE]))])


def TemplateEvaluate(o, t):
    """
    >>> TemplateEvaluate(Pixel(1), 1)
    Pixel(1)
    >>> TemplateEvaluate(Repeat(1, [Pixel(1)]), 1)
    Repeat(1, [Pixel(1)])
    >>> f = lambda t: Pixel(t)
    >>> TemplateEvaluate(f, 5)
    Pixel(5)
    >>> TemplateEvaluate(f, 10)
    Pixel(10)
    >>> g = Repeat(lambda t: 10-t, [Pixel(1)])
    >>> TemplateEvaluate(g, 1)
    Repeat(9, [Pixel(1)])
    >>> TemplateEvaluate(g, 9)
    Repeat(1, [Pixel(1)])
    >>> h = Repeat(lambda t: 10-t, [Repeat(lambda t: 10+t, [Pixel(1)]), Pixel(2)])
    >>> TemplateEvaluate(h, 1)
    Repeat(9, [Repeat(11, [Pixel(1)]), Pixel(2)])
    >>> TemplateEvaluate(h, 5)
    Repeat(5, [Repeat(15, [Pixel(1)]), Pixel(2)])
    """
    if callable(o):
        a = o(t)
        return a

    try:
        args = []
        for arg in o:
            args.append(TemplateEvaluate(arg, t))
        if len(args) == 1:
            return o.__class__(*args)
        return o.__class__(args)
    except TypeError as e:
        return o

def List2Image(list_1D, row_length, file_name):
	"""  Converts a 1D list with values in [0-255] to image data type and saves as .png file		
	>>> List2Image(Repeat(3000, [Repeat(2000, [Pixel(128)]), Repeat(2000, [Pixel(255)])]).gen(), 4000, 'new')
	"""
	list_1D = np.uint8(list_1D)
	im = Image.fromarray(np.reshape(list_1D,(-1,row_length)))
	im.save('%s.png' % file_name)

def Image2List(file_name):
    """
    >>> Image2List('new')[:10]
    """
    im = Image.open('%s.png' % file_name)
    list_1D = list(im.getdata())

    return list_1D

if __name__ == "__main__":
    import doctest
    doctest.testmod()
