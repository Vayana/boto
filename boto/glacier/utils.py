# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import hashlib
import math


_MEGABYTE = 1024 * 1024
DEFAULT_PART_SIZE = 4 * _MEGABYTE
MAXIMUM_NUMBER_OF_PARTS = 10000


def minimum_part_size(size_in_bytes):
    # The default part size (4 MB) will be too small for a very large
    # archive, as there is a limit of 10,000 parts in a multipart upload.
    # This puts the maximum allowed archive size with the default part size
    # at 40,000 MB. We need to do a sanity check on the part size, and find
    # one that works if the default is too small.
    part_size = _MEGABYTE
    if (DEFAULT_PART_SIZE * MAXIMUM_NUMBER_OF_PARTS) < size_in_bytes:
        if size_in_bytes > (4096 * _MEGABYTE * 10000):
            raise ValueError("File size too large: %s" % size_in_bytes)
        min_part_size = size_in_bytes / 10000
        power = 3
        while part_size < min_part_size:
            part_size = math.ldexp(_MEGABYTE, power)
            power += 1
        part_size = int(part_size)
    else:
        part_size = DEFAULT_PART_SIZE
    return part_size


def chunk_hashes(bytestring, chunk_size=_MEGABYTE):
    chunk_count = int(math.ceil(len(bytestring) / float(chunk_size)))
    hashes = []
    for i in range(chunk_count):
        start = i * chunk_size
        end = (i + 1) * chunk_size
        hashes.append(hashlib.sha256(bytestring[start:end].encode("utf-8")).digest())
    return hashes


def tree_hash(fo):
    """
    Given a hash of each 1MB chunk (from chunk_hashes) this will hash
    together adjacent hashes until it ends up with one big one. So a
    tree of hashes.
    """
    hashes = []
    hashes.extend(fo)
    while len(hashes) > 1:
        new_hashes = []
        while True:
            if len(hashes) > 1:
                first = hashes.pop(0)
                second = hashes.pop(0)
                new_hashes.append(hashlib.sha256(first + second).digest())
            elif len(hashes) == 1:
                only = hashes.pop(0)
                new_hashes.append(only)
            else:
                break
        hashes.extend(new_hashes)
    return hashes[0]


def compute_hashes_from_fileobj(fileobj, chunk_size=1024 * 1024):
    """Compute the linear and tree hash from a fileobj.

    This function will compute the linear/tree hash of a fileobj
    in a single pass through the fileobj.

    :param fileobj: A file like object.

    :param chunk_size: The size of the chunks to use for the tree
        hash.  This is also the buffer size used to read from
        `fileobj`.

    :rtype: tuple
    :return: A tuple of (linear_hash, tree_hash).  Both hashes
        are returned in hex.

    """
    linear_hash = hashlib.sha256()
    chunks = []
    chunk = fileobj.read(chunk_size)
    while chunk:
        linear_hash.update(chunk)
        chunks.append(hashlib.sha256(chunk).digest())
        chunk = fileobj.read(chunk_size)
    return linear_hash.hexdigest(), bytes_to_hex(tree_hash(chunks))


def bytes_to_hex(str_as_bytes):
    return ''.join(["%02x" % ord(x) for x in str_as_bytes]).strip()
