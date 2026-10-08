"""The Unnamed glyph alphabet (original designs) as tiny bitmaps."""

# Four ritual glyphs used by Glyph Dials and Cipher Stones (index = block state value).
GLYPHS = {
    0: [  # Star — a falling star with a downward tail
        '...#...',
        '.#.#.#.',
        '..###..',
        '#######',
        '..###..',
        '.#.#.#.',
        '...#...',
        '...#...',
        '...#...',
    ],
    1: [  # Eye — the watching, weeping eye
        '.......',
        '..###..',
        '.#...#.',
        '#..#..#',
        '.#...#.',
        '..###..',
        '...#...',
        '..#.#..',
        '.#...#.',
    ],
    2: [  # Mouth — lips sewn shut
        '.......',
        '.#####.',
        '#.....#',
        '#######',
        '.#.#.#.',
        '#######',
        '#.....#',
        '.#####.',
        '.......',
    ],
    3: [  # Lantern — the lantern kept for the star
        '...#...',
        '..###..',
        '.#####.',
        '.#.#.#.',
        '.##.##.',
        '.#.#.#.',
        '.#####.',
        '..###..',
        '...#...',
    ],
}

GLYPH_NAMES = {0: 'Star', 1: 'Eye', 2: 'Mouth', 3: 'Lantern'}

# The Weeping Eye — emblem of the Choir (used on chiseled stone, codex, pack icon)
WEEPING_EYE = [
    '...#####...',
    '.##.....##.',
    '#....#....#',
    '#...###...#',
    '#....#....#',
    '.##.....##.',
    '...#####...',
    '...#.#.#...',
    '...#...#...',
    '..#.....#..',
]

SEWN_MOUTH = [
    '.#######.',
    '#########',
    '.#.#.#.#.',
    '#########',
    '.#######.',
]
