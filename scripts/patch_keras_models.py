#!/usr/bin/env python2.7
"""
Patch BOTA Keras 0.x model JSON for Keras 1.2.2.

The key insight: Keras 1.2.2 Dense.get_output_shape_for() asserts:
    input_shape[-1] == self.input_dim
So input_dim must be set correctly on EVERY Dense layer, not just the first.
Each Dense layer's input_dim = the previous Dense layer's output_dim.

Usage:
    python2.7 patch_keras_models.py /path/to/models/
"""
import sys
import os
import json
import glob
import shutil

DROP_KEYS = ['custom_name', 'cache_enabled']
REMOVE_IF_NONE = ['W_constraint', 'b_constraint', 'W_regularizer',
                  'b_regularizer', 'activity_regularizer']


def get_raw_layers(data):
    """Extract flat layer list from either 0.x or already-converted 1.x format."""
    if isinstance(data, dict) and data.get('class_name') == 'Sequential':
        raw = []
        for lyr in data['config']:
            flat = dict(lyr['config'])
            flat['name'] = lyr['class_name']
            raw.append(flat)
        return raw
    return data.get('layers', [])


def patch_model(data):
    raw_layers = get_raw_layers(data)

    # Collect output_dims from all Dense layers in order
    dense_layers = [l for l in raw_layers if l.get('name') == 'Dense']
    dense_output_dims = [l.get('output_dim') for l in dense_layers]

    # Thread input_dims: first from input_shape, rest from previous output_dim
    dense_input_dims = []
    for i, lyr in enumerate(dense_layers):
        if i == 0:
            if lyr.get('input_shape'):
                dense_input_dims.append(lyr['input_shape'][-1])
            elif lyr.get('input_dim'):
                dense_input_dims.append(lyr['input_dim'])
            else:
                raise ValueError("Cannot determine input_dim for first Dense layer")
        else:
            dense_input_dims.append(dense_output_dims[i - 1])

    print("  Dense layer chain:")
    for i in range(len(dense_input_dims)):
        print("    Dense[%d]: input_dim=%s -> output_dim=%s" % (
            i, dense_input_dims[i], dense_output_dims[i]))

    # Build patched layer list
    new_layers = []
    dense_idx = 0
    for lyr in raw_layers:
        class_name = lyr['name']
        config = {}

        for k, v in lyr.items():
            if k in DROP_KEYS:
                continue
            if k == 'name':
                config['name'] = lyr.get('custom_name', class_name.lower())
                continue
            config[k] = v

        if class_name == 'Dense':
            config['input_dim'] = dense_input_dims[dense_idx]
            config.pop('input_shape', None)
            dense_idx += 1

        for key in REMOVE_IF_NONE:
            if key in config and config[key] is None:
                del config[key]

        new_layers.append({'class_name': class_name, 'config': config})

    return {'class_name': 'Sequential', 'config': new_layers}


def patch_file(path):
    backup = path + '.orig.bak'
    # Always restore from original backup if present to avoid double-patching
    if os.path.exists(backup):
        print("  Restoring from original backup first...")
        shutil.copy2(backup, path)

    with open(path, 'rb') as fh:
        data = json.load(fh)

    patched = patch_model(data)

    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print("  Backed up original: %s" % backup)

    with open(path, 'wb') as fh:
        json.dump(patched, fh, indent=2)

    print("  Written: %s" % path)


def main():
    if len(sys.argv) < 2:
        print("Usage: python2.7 patch_keras_models.py /path/to/models/")
        sys.exit(1)

    models_dir = sys.argv[1]
    if not os.path.isdir(models_dir):
        print("[ERROR] Not a directory: %s" % models_dir)
        sys.exit(1)

    json_files = glob.glob(os.path.join(models_dir, '*.model_arch.json'))
    if not json_files:
        print("[ERROR] No *.model_arch.json files found in: %s" % models_dir)
        sys.exit(1)

    print("Found %d model file(s):" % len(json_files))
    for f in sorted(json_files):
        print("\n[%s]" % os.path.basename(f))
        patch_file(f)

    print("\nDone.")


if __name__ == '__main__':
    main()
