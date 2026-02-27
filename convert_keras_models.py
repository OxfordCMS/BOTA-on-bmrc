#!/usr/bin/env python2.7
"""
Patch BOTA Keras model JSON files for Keras 1.2.2 compatibility.

Handles conversion from both Keras 0.x (flat layer list) and fixes
intermediate Dense layers that have input_dim=null, which causes:
  AssertionError in get_output_shape_for: input_shape[-1] == self.input_dim

Rules:
  - First Dense layer: derive input_dim from input_shape if null, remove input_shape
  - All other Dense layers: remove input_dim entirely if null
  - All layers: remove keys with null values that Keras 1.x doesn't expect
  - Wrap 0.x flat layers into {'class_name': X, 'config': {...}} structure

Usage:
    python2.7 patch_keras_models.py /path/to/models/
"""
import sys
import os
import json
import glob
import shutil

DROP_LAYER_KEYS = ['custom_name', 'cache_enabled']

# Keys that should be removed from ANY layer config if their value is None
# (Keras 1.x Dense will fail the input_dim assertion if it is None)
REMOVE_IF_NONE = ['input_dim', 'input_shape', 'W_constraint', 'b_constraint',
                  'W_regularizer', 'b_regularizer', 'activity_regularizer']


def patch_layer(flat, is_first):
    class_name = flat['name']

    config = {}
    for k, v in flat.items():
        if k in DROP_LAYER_KEYS:
            continue
        if k == 'name':
            config['name'] = flat.get('custom_name', class_name.lower())
            continue
        config[k] = v

    if class_name == 'Dense':
        if is_first:
            # Derive input_dim from input_shape if not set
            if not config.get('input_dim') and config.get('input_shape'):
                config['input_dim'] = config['input_shape'][-1]
            # input_shape is not a valid Dense config key in Keras 1.x
            config.pop('input_shape', None)
        else:
            # Intermediate Dense layers must NOT have input_dim at all
            config.pop('input_dim', None)
            config.pop('input_shape', None)

    # Remove any other null values that would confuse Keras 1.x
    for key in REMOVE_IF_NONE:
        if key in config and config[key] is None:
            del config[key]

    return {'class_name': class_name, 'config': config}


def patch_model(data):
    """
    Accept either:
      - 0.x format: {'layers': [...], 'loss': ..., ...}  (flat layer dicts)
      - already-converted but broken: {'class_name': 'Sequential', 'config': [...]}
    """
    # Unwrap already-converted format to get the raw layer list
    if isinstance(data, dict) and data.get('class_name') == 'Sequential':
        # config is already a list of {class_name, config} dicts
        # Re-extract flat representation so we can patch uniformly
        raw_layers = []
        for lyr in data['config']:
            flat = dict(lyr['config'])
            flat['name'] = lyr['class_name']
            raw_layers.append(flat)
    else:
        raw_layers = data.get('layers', [])

    new_layers = []
    first_dense_seen = False
    for layer in raw_layers:
        class_name = layer.get('name', layer.get('class_name', ''))
        is_first = (class_name == 'Dense' and not first_dense_seen)
        if class_name == 'Dense':
            first_dense_seen = True
        new_layers.append(patch_layer(layer, is_first))

    return {'class_name': 'Sequential', 'config': new_layers}


def patch_file(path):
    backup = path + '.orig.bak'

    with open(path, 'rb') as fh:
        data = json.load(fh)

    patched = patch_model(data)

    # Back up original only once
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print("  Backed up original: %s" % backup)

    with open(path, 'wb') as fh:
        json.dump(patched, fh, indent=2)

    # Report first Dense layer config for verification
    for lyr in patched['config']:
        if lyr['class_name'] == 'Dense':
            cfg = lyr['config']
            print("  First Dense: input_dim=%s  output_dim=%s  name=%s" % (
                cfg.get('input_dim', 'MISSING'),
                cfg.get('output_dim', 'MISSING'),
                cfg.get('name', '?'),
            ))
            break

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

    print("\nDone. Originals in *.orig.bak")


if __name__ == '__main__':
    main()
