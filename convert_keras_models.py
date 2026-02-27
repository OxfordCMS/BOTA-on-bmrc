#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""
Convert BOTA Keras 0.x model JSON to Keras 1.2.2 format.

Keras 0.x stores layers as flat dicts with 'name' and 'custom_name'.
Keras 1.x wraps each layer as {'class_name': X, 'config': {...}}.

Usage:
    python2.7 convert_keras_models.py /path/to/models/
"""
import sys
import os
import json
import glob
import shutil

# Keys to remove from the flat 0.x layer dict before putting into 'config'
DROP_KEYS = ['name', 'custom_name', 'cache_enabled']

# Keys to rename inside the layer config (0.x -> 1.x)
RENAME = {
    'output_dim':    'output_dim',   # kept same in 1.x
    'init':          'init',         # kept same in 1.x
    'W_constraint':  'W_constraint',
    'b_constraint':  'b_constraint',
    'W_regularizer': 'W_regularizer',
    'b_regularizer': 'b_regularizer',
    'activity_regularizer': 'activity_regularizer',
}


def convert_layer(flat):
    class_name = flat.get('name', 'Unknown')
    config = {}
    for k, v in flat.items():
        if k in DROP_KEYS:
            continue
        config[k] = v
    # Give the layer an instance name
    config['name'] = flat.get('custom_name', class_name.lower())
    return {'class_name': class_name, 'config': config}


def convert_model(old):
    """
    Keras 0.x top-level keys: layers, loss, optimizer, name, sample_weight_mode
    Keras 1.x Sequential.from_config expects: class_name + config with layers list
    """
    new_layers = []
    for layer in old.get('layers', []):
        new_layers.append(convert_layer(layer))

    return {
        'class_name': 'Sequential',
        'config': new_layers
    }


def convert_file(path):
    backup = path + '.keras0x.bak'
    with open(path, 'rb') as fh:
        data = json.load(fh)

    # Already has class_name at top level -> already converted or 1.x format
    if isinstance(data, dict) and 'class_name' in data:
        print("  SKIP (already 1.x format): %s" % path)
        return

    converted = convert_model(data)

    shutil.copy2(path, backup)
    print("  Backed up: %s" % backup)

    with open(path, 'wb') as fh:
        json.dump(converted, fh, indent=2)

    print("  Converted: %s" % path)


def main():
    if len(sys.argv) < 2:
        print("Usage: python2.7 convert_keras_models.py /path/to/models/")
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
        convert_file(f)

    print("\nDone. Originals backed up as *.keras0x.bak")


if __name__ == '__main__':
    main()
