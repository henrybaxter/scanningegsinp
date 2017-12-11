import sys
import math
import os
import shutil
import argparse
import logging

import toml

from . import egsinp

logger = logging.getLogger(__name__)

DIR = os.path.dirname(__file__)
DEFAULT_OPTIONS = os.path.join(DIR, 'options.toml')
DEFAULT_TEMPLATE = os.path.join(DIR, 'template.egsinp')

print(DEFAULT_OPTIONS)


def generate_y(target_length, spacing, reflect):
    logger.info('Generating beam positions')
    offset = spacing / 2
    y = offset
    ymax = target_length / 2
    i = 0
    result = []
    while y < ymax:
        result.append(y)
        i += 1
        y = i * spacing + offset
    if not reflect:
        # need to reflect y values if not using reflection optimization
        for y in result[:]:
            result.insert(0, -y)
    logger.info('Generated {} y values'.format(len(result)))
    return result


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--make-template', action='store_true')
    parser.add_argument('--make-options', action='store_true')
    parser.add_argument('--toml', default="options.toml")
    parser.add_argument('--template', default="template.egsinp")
    args = parser.parse_args()
    if args.make_template:
        shutil.copy(DEFAULT_TEMPLATE, args.template)
    if args.make_options:
        shutil.copy(DEFAULT_OPTIONS, args.toml)
    try:
        options = toml.load(open(args.toml))
    except FileNotFoundError:
        print('Could not find {}, try running with --make-options'.format(args.toml))
        sys.exit(1)
    options.update(vars(args))
    floats = [
        'beam-width', 'beam-height', 'beam-gap',
        'target-distance', 'target-length', 'target-angle'
    ]
    ints = [
        'histories'
    ]
    for key in floats:
        options[key] = float(options[key])
    for key in ints:
        options[key] = int(options[key])
    return options


def generate_templates(args, y_values):
    try:
        template = egsinp.parse_egsinp(open(args['template']).read())
    except FileNotFoundError:
        print('Could not find {}, try running with --make-template', args['template'])
        sys.exit(1)
    template['ncase'] = args['beamlet-histories']
    template['ybeam'] = args['beam-width'] / 2
    template['zbeam'] = args['beam-height'] / 2
    xtube = template['cms'][0]
    xtube['rmax_cm'] = min(xtube['rmax_cm'], args['target-length'] / 2)
    xtube['angelei'] = args['target-angle']
    template['title'] = args['name']
    if os.path.exists(args['folder']):
        shutil.rmtree(args['folder'])
    os.makedirs(args['folder'])
    for i, y in enumerate(y_values):
        theta = math.atan(y / args['target-distance'])
        cos_x = -math.cos(theta)
        cos_y = math.copysign(math.sqrt(1 - cos_x * cos_x), y)
        template['uinc'] = cos_x
        template['vinc'] = cos_y
        fn = os.path.join(args['folder'], '{}.egsinp'.format(i))
        logger.debug('Writing to {}'.format(fn))
        with open(fn, 'w') as f:
            f.write(egsinp.unparse_egsinp(template))


def main():
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    y_values = generate_y(
        args['target-length'],
        args['beam-width'] + args['beam-gap'],
        args['reflect-later']
    )
    args['beamlet-count'] = len(y_values) * (1 if not args['reflect-later'] else 2)
    args['beamlet-histories'] = args['histories'] // args['beamlet-count']
    args['total-histories'] = args['beamlet-histories'] * args['beamlet-count']
    logger.info('Will generate {} templates with {} histories each for a total of {} histories'.format(
        len(y_values),
        args['beamlet-histories'],
        args['total-histories']
    ))
    if args['reflect-later']:
        logger.info('This total after reflection!')
    generate_templates(args, y_values)


if __name__ == '__main__':
    main()
