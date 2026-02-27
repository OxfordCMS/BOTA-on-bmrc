#!/usr/bin/env python2.7
"""
Rebuild BOTA Keras model JSON using Keras 1.2.2 native format.

Instead of trying to convert the old JSON, we build the model
programmatically from the known architecture, load the weights
from the .h5 file, then re-save the JSON using model.to_json().
This guarantees the JSON is in exactly the format Keras 1.2.2 expects.

Architecture (read from the original JSON):
  Dense(9 -> 512, linear) -> Activation(relu) -> Dropout(0.5)
  Dense(512 -> 1024, linear) -> Activation(relu) -> Dropout(0.2)
  Dense(1024 -> 128, linear) -> Activation(relu) -> Dropout(0.2)
  Dense(128 -> 2, linear) -> Activation(softmax)

Usage:
    python2.7 rebuild_keras_models.py /path/to/models/
"""
import sys
import os
import json
import glob
import shutil

import keras
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation


def build_model_from_json(json_path):
    """
    Parse the layer list from the JSON and build a fresh Sequential model.
    Returns (model, layer_configs) where layer_configs is the list of layer dicts.
    """
    with open(json_path, 'rb') as fh:
        data = json.load(fh)

    # Get layer list — handle both 0.x and partially-converted formats
    if data.get('class_name') == 'Sequential':
        layers = data['config']
    else:
        layers = data.get('layers', [])

    model = Sequential()
    first_dense = True

    for lyr in layers:
        # Support both flat 0.x (name key) and 1.x (class_name key) formats
        cname = lyr.get('class_name') or lyr.get('name')
        cfg   = lyr.get('config', lyr)  # 0.x has no 'config' wrapper

        if cname == 'Dense':
            output_dim = cfg.get('output_dim')
            activation = cfg.get('activation', 'linear')
            init       = cfg.get('init', 'glorot_uniform')
            if first_dense:
                input_dim = cfg.get('input_dim')
                if not input_dim and cfg.get('input_shape'):
                    input_dim = cfg['input_shape'][-1]
                model.add(Dense(output_dim,
                                input_dim=input_dim,
                                activation=activation,
                                init=init))
                first_dense = False
            else:
                model.add(Dense(output_dim,
                                activation=activation,
                                init=init))

        elif cname == 'Activation':
            model.add(Activation(cfg.get('activation')))

        elif cname == 'Dropout':
            p = cfg.get('p') or cfg.get('rate', 0.5)
            model.add(Dropout(p))

        else:
            print("  WARNING: unknown layer type '%s', skipping" % cname)

    return model


def rebuild_file(json_path, h5_path):
    json_backup = json_path + '.orig.bak'

    # Back up original JSON if not already done
    if not os.path.exists(json_backup):
        shutil.copy2(json_path, json_backup)
        print("  JSON backed up: %s" % json_backup)

    print("  Building model from architecture...")
    model = build_model_from_json(json_path)
    model.summary()

    print("  Loading weights from: %s" % h5_path)
    model.load_weights(h5_path)
    print("  Weights loaded OK")

    # Re-save JSON using Keras 1.2.2 native to_json()
    native_json = model.to_json()
    with open(json_path, 'wb') as fh:
        fh.write(native_json)
    print("  JSON re-saved in native Keras 1.2.2 format: %s" % json_path)

    # Verify by reloading
    print("  Verifying reload...")
    from keras.models import model_from_json
    test_model = model_from_json(open(json_path).read())
    test_model.load_weights(h5_path)
    print("  Verification OK - model loads cleanly")


def main():
    if len(sys.argv) < 2:
        print("Usage: python2.7 rebuild_keras_models.py /path/to/models/")
        sys.exit(1)

    models_dir = sys.argv[1]
    if not os.path.isdir(models_dir):
        print("[ERROR] Not a directory: %s" % models_dir)
        sys.exit(1)

    json_files = sorted(glob.glob(os.path.join(models_dir, '*.model_arch.json')))
    if not json_files:
        print("[ERROR] No *.model_arch.json files found in: %s" % models_dir)
        sys.exit(1)

    print("Found %d model file(s):" % len(json_files))
    for json_path in json_files:
        allele = os.path.basename(json_path).replace('.model_arch.json', '')
        h5_path = os.path.join(models_dir, '%s.model_weights.h5' % allele)

        print("\n[%s]" % allele)

        if not os.path.exists(h5_path):
            print("  ERROR: weights file not found: %s" % h5_path)
            continue

        # Restore from backup before rebuilding if backup exists
        json_backup = json_path + '.orig.bak'
        if os.path.exists(json_backup):
            print("  Restoring from backup first...")
            shutil.copy2(json_backup, json_path)

        rebuild_file(json_path, h5_path)

    print("\nAll done.")


if __name__ == '__main__':
    main()
