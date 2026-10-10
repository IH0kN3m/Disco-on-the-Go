"""Merge shader registrations with explicit serialized-file ownership."""
ANDROID_DISABLED_BUILTINS={
    'Hidden/VideoDecodeOSX':(16002,'macOS rectangle-texture decoder; Android uses VideoDecodeAndroid'),
    'Hidden/VR/BlitFromTex2DToTexArraySlice':(15312,'VR builtin requires unsupported desktop layer extension; VR is outside the Android game target'),
}


def disabled_android_builtin(name,path_id):
    policy=ANDROID_DISABLED_BUILTINS.get(name)
    if not policy:return None
    if path_id!=policy[0]:raise ValueError('Unsupported builtin shader object ownership')
    return policy[1]


def merge_builtin_registry(current, donor, donor_file, target_file, shader_names):
    result = [(dict(pointer), name) for pointer, name in current]
    for pointer, name in donor:
        if pointer['m_FileID'] != donor_file or pointer['m_PathID'] == 0:
            continue
        path = pointer['m_PathID']
        if shader_names.get(path) != name:
            raise ValueError('Shader registration does not match owned object')
        replacement = {'m_FileID': target_file, 'm_PathID': path}
        matches = [i for i, (_, existing) in enumerate(result) if existing == name]
        if matches:
            # Unity can register both a builtin and a game-owned shader name.
            # Retain game registrations; validate existing builtin ownership.
            for index in matches:
                old = result[index][0]
                if old['m_PathID'] and old['m_FileID'] == target_file and old != replacement:
                    raise ValueError('Shader name ownership collision')
            if not any(result[i][0]['m_PathID'] for i in matches):
                result[matches[0]] = (replacement, name)
        else:
            result.append((replacement, name))
    return result
