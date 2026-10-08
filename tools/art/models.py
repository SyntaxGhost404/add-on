"""Block and entity geometry definitions."""
from .geo import Bone, Cube, Geometry


def face_uv_full(u=0, v=0, size=16, side_v=None):
    """Per-face UV covering a 16x16 texture on top/bottom and thin strips on the sides."""
    return None


# --------------------------------------------------------------------------- blocks

def hushing_plate():
    uv = {
        'up': {'uv': [0, 0], 'uv_size': [16, 16]},
        'down': {'uv': [0, 0], 'uv_size': [16, 16]},
        'north': {'uv': [0, 15], 'uv_size': [16, 1]},
        'south': {'uv': [0, 15], 'uv_size': [16, 1]},
        'east': {'uv': [0, 15], 'uv_size': [16, 1]},
        'west': {'uv': [0, 15], 'uv_size': [16, 1]},
    }
    return Geometry('geometry.rotu.hushing_plate', 16, 16, [
        Bone('plate', [0, 0, 0], cubes=[Cube('plate', [-8, 0, -8], [16, 1, 16], face_uv=uv)])
    ], visible=(1, 1, (0, 0.5, 0)))


def funerary_urn():
    cubes = [
        Cube('foot', [-3, 0, -3], [6, 1, 6], style='clay_dark'),
        Cube('base', [-4, 1, -4], [8, 2, 8], style='clay_band'),
        Cube('body', [-5, 3, -5], [10, 7, 10], style='clay_body'),
        Cube('shoulder', [-4, 10, -4], [8, 1, 8], style='clay_band'),
        Cube('neck', [-3, 11, -3], [6, 2, 6], style='clay_dark'),
        Cube('lip', [-3.5, 13, -3.5], [7, 1, 7], style='clay_band'),
        Cube('knob', [-1, 14, -1], [2, 1, 2], style='clay_knob'),
    ]
    return Geometry('geometry.rotu.funerary_urn', 64, 64,
                    [Bone('urn', [0, 0, 0], cubes=cubes)], visible=(1, 1, (0, 0.5, 0))).pack()


def scriptorium_desk():
    cubes = [
        Cube('leg_a', [-7, 0, -6], [2, 10, 2], style='wood_dark'),
        Cube('leg_b', [5, 0, -6], [2, 10, 2], style='wood_dark'),
        Cube('leg_c', [-7, 0, 4], [2, 10, 2], style='wood_dark'),
        Cube('leg_d', [5, 0, 4], [2, 10, 2], style='wood_dark'),
        Cube('shelf', [-6, 3, -5], [12, 1, 10], style='wood'),
        Cube('top', [-8, 10, -7], [16, 2, 14], style='wood_top'),
        Cube('rest', [-5, 12, -4], [10, 1, 6], pivot=[0, 12, -1], rotation=[-22.5, 0, 0], style='stone'),
        Cube('book', [-4, 13, -3.5], [8, 1, 5], pivot=[0, 12, -1], rotation=[-22.5, 0, 0], style='book'),
        Cube('tablet', [-3, 12, 3], [5, 1, 3], style='tablet'),
        Cube('candle', [5, 12, 3], [1, 3, 1], style='candle'),
        Cube('flame', [5.25, 15, 3.25], [0.5, 1, 0.5], style='flame'),
    ]
    return Geometry('geometry.rotu.scriptorium_desk', 64, 64,
                    [Bone('desk', [0, 0, 0], cubes=cubes)], visible=(1, 1, (0, 0.5, 0))).pack()


def reliquary():
    cubes = [
        Cube('plinth', [-7, 0, -7], [14, 2, 14], style='stone_dark'),
        Cube('body', [-6, 2, -6], [12, 7, 12], style='casket'),
        Cube('post_a', [-7, 2, -7], [2, 9, 2], style='gilt'),
        Cube('post_b', [5, 2, -7], [2, 9, 2], style='gilt'),
        Cube('post_c', [-7, 2, 5], [2, 9, 2], style='gilt'),
        Cube('post_d', [5, 2, 5], [2, 9, 2], style='gilt'),
        Cube('lid', [-6.5, 9, -6.5], [13, 2, 13], style='lid'),
        Cube('crown', [-4, 11, -4], [8, 1, 8], style='stone_dark'),
        Cube('core', [-1, 12, -1], [2, 2, 2], style='core'),
    ]
    return Geometry('geometry.rotu.reliquary', 64, 64,
                    [Bone('reliquary', [0, 0, 0], cubes=cubes)], visible=(1, 1, (0, 0.5, 0))).pack()


BLOCK_MODELS = [hushing_plate, funerary_urn, scriptorium_desk, reliquary]


# --------------------------------------------------------------------------- entities

def hushwalker():
    bones = [
        Bone('root', [0, 0, 0]),
        Bone('body', [0, 24, 0], parent='root', cubes=[
            Cube('torso', [-4, 12, -2], [8, 12, 4], style='robe_torso'),
            Cube('robe', [-4.5, 6, -2.5], [9, 6, 5], style='robe_skirt'),
        ]),
        Bone('head', [0, 24, 0], parent='body', rotation=[12, 0, 0], cubes=[
            Cube('head', [-4, 24, -4], [8, 8, 8], style='hw_face'),
            Cube('hood', [-4, 24, -4], [8, 8, 8], inflate=0.6, style='hw_hood'),
        ]),
        Bone('rightArm', [-5.5, 22.5, 0], parent='body', cubes=[
            Cube('right_arm', [-7, 9, -1.5], [3, 14, 3], style='hw_arm')]),
        Bone('leftArm', [5.5, 22.5, 0], parent='body', cubes=[
            Cube('left_arm', [4, 9, -1.5], [3, 14, 3], style='hw_arm')]),
        Bone('rightLeg', [-2, 12, 0], parent='root', cubes=[
            Cube('right_leg', [-4, 0, -2], [4, 12, 4], style='hw_leg')]),
        Bone('leftLeg', [2, 12, 0], parent='root', cubes=[
            Cube('left_leg', [0, 0, -2], [4, 12, 4], style='hw_leg')]),
    ]
    return Geometry('geometry.rotu.hushwalker', 64, 64, bones, visible=(2, 3, (0, 1.2, 0))).pack()


def murmur():
    bones = [
        Bone('root', [0, 0, 0]),
        Bone('body', [0, 10, 0], parent='root', cubes=[
            Cube('torso', [-2.5, 9, -1.5], [5, 6, 3], style='mm_torso')]),
        Bone('head', [0, 15, 0], parent='body', cubes=[
            Cube('head', [-3, 15, -3], [6, 6, 6], style='mm_face'),
            Cube('hood', [-3, 15, -3], [6, 6, 6], inflate=0.5, style='mm_hood')]),
        Bone('tail1', [0, 9, 0], parent='body', cubes=[
            Cube('tail1', [-2, 5, -1], [4, 4, 2], style='mm_tail')]),
        Bone('tail2', [0, 5, 0], parent='tail1', cubes=[
            Cube('tail2', [-1, 1, -0.5], [2, 4, 1], style='mm_tail_end')]),
        Bone('rightArm', [-3, 14, 0], parent='body', cubes=[
            Cube('right_arm', [-4.5, 7, -0.75], [1.5, 7, 1.5], style='mm_arm')]),
        Bone('leftArm', [3, 14, 0], parent='body', cubes=[
            Cube('left_arm', [3, 7, -0.75], [1.5, 7, 1.5], style='mm_arm')]),
    ]
    return Geometry('geometry.rotu.murmur', 64, 32, bones, visible=(1.5, 2, (0, 0.6, 0))).pack()


def graven_sentinel():
    bones = [
        Bone('root', [0, 0, 0]),
        Bone('body', [0, 14, 0], parent='root', cubes=[
            Cube('torso', [-8, 14, -5], [16, 16, 10], style='gs_torso'),
            Cube('belt', [-7, 12, -4], [14, 2, 8], style='gs_band'),
        ]),
        Bone('head', [0, 30, 0], parent='body', cubes=[
            Cube('head', [-5, 30, -5], [10, 10, 10], style='gs_face'),
            Cube('crest', [-6, 40, -1.5], [12, 3, 3], style='gs_band'),
        ]),
        Bone('rightArm', [-9, 28, 0], parent='body', cubes=[
            Cube('right_shoulder', [-15, 26, -4], [7, 5, 8], style='gs_band'),
            Cube('right_arm', [-14, 5, -3], [6, 21, 6], style='gs_arm'),
        ]),
        Bone('leftArm', [9, 28, 0], parent='body', cubes=[
            Cube('left_shoulder', [8, 26, -4], [7, 5, 8], style='gs_band'),
            Cube('left_arm', [8, 5, -3], [6, 21, 6], style='gs_arm'),
        ]),
        Bone('rightLeg', [-4, 14, 0], parent='root', cubes=[
            Cube('right_leg', [-7, 0, -3], [6, 14, 6], style='gs_leg')]),
        Bone('leftLeg', [4, 14, 0], parent='root', cubes=[
            Cube('left_leg', [1, 0, -3], [6, 14, 6], style='gs_leg')]),
    ]
    return Geometry('geometry.rotu.graven_sentinel', 128, 64, bones, visible=(3, 4, (0, 1.5, 0))).pack()


def last_cantor():
    bones = [
        Bone('root', [0, 0, 0]),
        Bone('body', [0, 20, 0], parent='root', cubes=[
            Cube('hem', [-7, 0, -5], [14, 4, 10], style='lc_hem'),
            Cube('skirt', [-6, 4, -4], [12, 16, 8], style='lc_robe'),
            Cube('torso', [-5, 20, -3], [10, 12, 6], style='lc_torso'),
            Cube('collar', [-6, 31, -4], [12, 3, 8], style='lc_gold'),
        ]),
        Bone('head', [0, 34, 0], parent='body', cubes=[
            Cube('head', [-4, 34, -4], [8, 9, 8], style='lc_head'),
            Cube('mask', [-3.5, 35, -4.6], [7, 7, 1], style='lc_mask'),
            Cube('hood', [-4.5, 40, -4.5], [9, 10, 9], style='lc_hood'),
            Cube('hood_tip', [-3, 50, -3], [6, 4, 6], style='lc_hood'),
        ]),
        Bone('halo', [0, 47, 0], parent='head', cubes=[
            Cube('halo_n', [-4, 46.5, -9], [8, 1, 1], style='lc_halo'),
            Cube('halo_s', [-4, 46.5, 8], [8, 1, 1], style='lc_halo'),
            Cube('halo_e', [8, 46.5, -4], [1, 1, 8], style='lc_halo'),
            Cube('halo_w', [-9, 46.5, -4], [1, 1, 8], style='lc_halo'),
            Cube('halo_ne', [4, 46.5, -8], [4, 1, 1], pivot=[6, 47, -7.5], rotation=[0, -45, 0], style='lc_halo'),
            Cube('halo_nw', [-8, 46.5, -8], [4, 1, 1], pivot=[-6, 47, -7.5], rotation=[0, 45, 0], style='lc_halo'),
            Cube('halo_se', [4, 46.5, 7], [4, 1, 1], pivot=[6, 47, 7.5], rotation=[0, 45, 0], style='lc_halo'),
            Cube('halo_sw', [-8, 46.5, 7], [4, 1, 1], pivot=[-6, 47, 7.5], rotation=[0, -45, 0], style='lc_halo'),
        ]),
        Bone('rightArm', [-6, 31, 0], parent='body', cubes=[
            Cube('right_sleeve', [-9, 22, -2], [3, 10, 4], style='lc_robe'),
            Cube('right_hand', [-8.5, 12, -1.5], [2, 10, 3], style='lc_hand'),
        ]),
        Bone('leftArm', [6, 31, 0], parent='body', cubes=[
            Cube('left_sleeve', [6, 22, -2], [3, 10, 4], style='lc_robe'),
            Cube('left_hand', [6.5, 12, -1.5], [2, 10, 3], style='lc_hand'),
        ]),
    ]
    return Geometry('geometry.rotu.last_cantor', 128, 128, bones, visible=(3, 5, (0, 2, 0))).pack()


def hush_bolt():
    bones = [Bone('bolt', [0, 2, 0], cubes=[
        Cube('core', [-1.5, 0.5, -1.5], [3, 3, 3], style='bolt_core'),
        Cube('shell', [-2.5, -0.5, -2.5], [5, 5, 5], style='bolt_shell'),
    ])]
    return Geometry('geometry.rotu.hush_bolt', 32, 32, bones, visible=(1, 1, (0, 0.2, 0))).pack()


ENTITY_MODELS = {
    'hushwalker': hushwalker,
    'murmur': murmur,
    'graven_sentinel': graven_sentinel,
    'last_cantor': last_cantor,
    'hush_bolt': hush_bolt,
}
