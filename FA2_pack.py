#!/usr/bin/env python3
import os
import sys
import struct

# Align size to a 16-byte boundary.
def align16(size):
    return (size + 0xF) & ~0xF

def pack_fa2(directory, output_file):
    # List all files in the given directory (non-recursive)
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    files.sort()  # sort by filename for determinism

    file_entries = []  # store tuple: (name_bytes, orig_size, stored_size, data_offset)
    file_data = bytearray()

    # Data area always starts at offset 0x10 (16)
    data_offset = 0x10

    for fname in files:
        full_path = os.path.join(directory, fname)
        with open(full_path, "rb") as f:
            data = f.read()
        orig_size = len(data)
        stored_size = orig_size  # no compression in our packer

        # Write file data into the file_data section.
        file_entries.append((fname, orig_size, stored_size, data_offset))
        file_data.extend(data)
        # Add padding to align on 16-byte boundary if necessary.
        pad_len = align16(orig_size) - orig_size
        if pad_len:
            file_data.extend(b"\0" * pad_len)
        data_offset += align16(orig_size)

    file_count = len(file_entries)
    # The index table is placed immediately after all file data.
    index_offset = data_offset

    # Build header (16 bytes)
    # Signature: 0x00324146, Flags: 0, Index offset, File count.
    header = struct.pack("<I", 0x00324146)  # Signature (little-endian)
    header += struct.pack("<I", 0)          # Flags (0 means index not compressed)
    header += struct.pack("<I", index_offset)  # Index offset
    header += struct.pack("<I", file_count)    # File count

    # Build index table. Each entry is 32 bytes.
    # Entry layout:
    #   15 bytes: file name as C-string (null-terminated and padded to 15 bytes)
    #   9 bytes: reserved (first byte is flag; set to 0 for uncompressed, remaining 8 bytes as 0)
    #   4 bytes: Unpacked size (uint32)
    #   4 bytes: File size (uint32)
    index_table = bytearray()
    for fname, orig_size, stored_size, f_offset in file_entries:
        # Encode file name using UTF-8. Use at most 14 bytes + null terminator.
        name_bytes = fname.encode("utf-8")
        if len(name_bytes) >= 15:
            # Truncate to 14 bytes and add a null byte.
            name_bytes = name_bytes[:14] + b"\0"
        else:
            name_bytes += b"\0"
        # Pad to 15 bytes.
        name_bytes = name_bytes.ljust(15, b"\0")
        index_table.extend(name_bytes)
        # Reserved 9 bytes: first byte is flags (0, since file not packed) and 8 bytes padding.
        index_table.extend(b"\0" * 9)
        # Now two 4-byte values: unpacked size and file size (both same in uncompressed archive).
        index_table.extend(struct.pack("<I", orig_size))
        index_table.extend(struct.pack("<I", stored_size))
        # Total for each entry: 15 + 9 + 4 + 4 = 32 bytes.

    # Write out the final archive.
    with open(output_file, "wb") as out:
        out.write(header)
        out.write(file_data)
        out.write(index_table)
    print(f"FA2 archive '{output_file}' created successfully with {file_count} file(s).")

def main():
    if len(sys.argv) < 3:
        print("Usage: python fa2_pack.py <directory> <output_file>")
        sys.exit(1)
    directory = sys.argv[1]
    output_file = sys.argv[2]
    if not os.path.isdir(directory):
        print("Error: Directory does not exist.")
        sys.exit(1)
    pack_fa2(directory, output_file)

if __name__ == "__main__":
    main()
